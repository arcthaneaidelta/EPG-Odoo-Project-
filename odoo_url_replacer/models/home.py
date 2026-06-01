import json
import logging
import psycopg2
import threading
from odoo import tools
from odoo.addons.base.models.ir_http import _logger, FasterRule, IrHttp
from odoo.addons.web.controllers.home import Home
import odoo
from odoo import http
from odoo.http import ROUTING_KEYS
from odoo.tools.misc import submap
import odoo.exceptions
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools.translate import _
from odoo.modules.registry import Registry
from odoo import api, fields, models, _
from odoo.tools import transpile_javascript
from odoo.addons.base.models import ir_config_parameter
from odoo.addons.base.models.assetsbundle import JavascriptAsset
import werkzeug.utils
import werkzeug.routing
import werkzeug.exceptions
import werkzeug
import re

base_sorturl = ['odoo']

import odoo.tools.config

def _init_base_sorturl():
	"""Read config from DB at startup so base_sorturl[0] is correct before first request."""
	try:
		db = odoo.tools.config['db_name']
		if db:
			import psycopg2
			conn = psycopg2.connect(f"dbname={db}")
			cur = conn.cursor()
			cur.execute(
				"SELECT value FROM ir_config_parameter WHERE key = 'web.url.replace.enabled'"
			)
			enabled_row = cur.fetchone()
			cur.execute(
				"SELECT value FROM ir_config_parameter WHERE key = 'web.base.sorturl'"
			)
			text_row = cur.fetchone()
			conn.close()
			if enabled_row and enabled_row[0] == 'True' and text_row and text_row[0]:
				base_sorturl[0] = text_row[0]
	except Exception:
		pass  # DB not ready yet — will be set on first routing_map() call

_init_base_sorturl()

class HomeController(Home):
	
	@http.route('/web/login', type='http', auth='none', sitemap=False)
	def web_login(self, redirect=None, **kw):
		# Get replacement text
		replacement = base_sorturl[0]
		
		# If a redirect was passed pointing to /odoo, rewrite it before passing upstream
		if redirect and replacement != 'odoo':
			redirect = re.sub(r'^/odoo(?=/|$)', '/' + replacement, redirect)
			redirect = re.sub(r'^/en/odoo(?=/|$)', '/en/' + replacement, redirect)
		
		response = super().web_login(redirect=redirect, **kw)
		
		# Rewrite the Location header in any redirect response
		if replacement != 'odoo' and hasattr(response, 'location') and response.location:
			response.location = re.sub(
				r'(/en)?/odoo(?=/|$)', 
				lambda m: (m.group(1) or '') + '/' + replacement, 
				response.location
			)
		
		return response


class IrConfigParameter(models.Model):
	_inherit = "ir.config_parameter"

	def write(self, vals):
		data = super(IrConfigParameter, self).write(vals)
		if self.key in ['web.base.sorturl', 'web.url.replace.enabled']:
			config = self.env['ir.config_parameter'].sudo()
			enabled = config.get_param("web.url.replace.enabled", "False") == "True"
			text = config.get_param("web.base.sorturl", "")
			base_sorturl[0] = text if (enabled and text) else 'odoo'
			self.env['ir.http'].env.registry.clear_cache("routing")
			self.env['ir.attachment'].regenerate_assets_bundles()
		return data


def _get_replacement_text(env=None):
	"""Helper to fetch the current Replacement Text safely."""
	if env:
		config = env['ir.config_parameter'].sudo()
		enabled = config.get_param("web.url.replace.enabled", "False") == "True"
		text = config.get_param("web.base.sorturl", "")
		if enabled and text:
			return text
	return base_sorturl[0]


@property
def content(self):
	content = super(JavascriptAsset, self).content
	replacement_text = _get_replacement_text(getattr(self, 'bundle', None) and self.bundle.env)

	if replacement_text != 'odoo':
		if self.name == "/web/static/src/core/browser/router.js":
			# ── router.js has multiple patterns that ALL need replacing ──
			#
			# Line 153: const start_url = ... ? "scoped_app" : "odoo";
			# Line 184: if (["odoo", "scoped_app"].includes(prefix))
			# Line 330: browser.location.pathname.startsWith("/odoo")
			# Line 331: ["/web", "/odoo"].includes(url.pathname) || url.pathname.startsWith("/odoo/")
			# Line 336: if (url.pathname.startsWith("/odoo")
			#
			# 1. Replace the start_url assignment (bare "odoo" without slash)
			content = content.replace(': "odoo"', ': "' + replacement_text + '"')
			# 2. Replace the prefix check array
			content = content.replace('["odoo",', '["' + replacement_text + '",')
			# 3. Replace all pathname comparisons with /odoo
			content = content.replace('"/odoo/"', '"/' + replacement_text + '/"')
			content = content.replace('"/odoo"', '"/' + replacement_text + '"')
			content = content.replace("'/odoo/'", "'/" + replacement_text + "/'")
			content = content.replace("'/odoo'", "'/" + replacement_text + "'")
			# 4. Handle the hashPrefix routing constant
			content = content.replace("hashPrefix = 'odoo'", "hashPrefix = '" + replacement_text + "'")
			content = content.replace('hashPrefix = "odoo"', 'hashPrefix = "' + replacement_text + '"')
		if self.name == "/web/static/src/webclient/navbar/navbar.js":
			content = content.replace("'/odoo'", "'/" + replacement_text + "'")
			content = content.replace('"/odoo"', '"/' + replacement_text + '"')

	if self.is_transpiled:
		if not self._converted_content:
			self._converted_content = transpile_javascript(self.url, content)
		return self._converted_content
	return content


JavascriptAsset.content = content


def url_init(self, httprequest):
	# During __init__, we don't have env yet, so we rely on the last known base_sorturl[0]
	# This is updated during routing_map generation (which happens early)
	replacement = base_sorturl[0]
	if replacement and replacement != 'odoo':
		# If the browser mistakenly sends /odoo, rewrite it to our custom prefix
		# so it matches the rewritten routing map.
		new_path = re.sub(r'^/odoo(?=/|$)', '/' + replacement, httprequest.path)
		httprequest.path = new_path
	
	self.httprequest = httprequest
	self.future_response = http.FutureResponse()
	self.dispatcher = http._dispatchers['http'](self)
	self.geoip = http.GeoIP(httprequest.remote_addr)
	self.registry = None
	self.env = None


http.Request.__init__ = url_init


@tools.ormcache('key', cache='routing')
def routing_map(self, key=None):
	# Initialize base_sorturl[0] from config on every routing map generation
	config_parameter = self.env['ir.config_parameter']
	enabled = config_parameter.sudo().get_param("web.url.replace.enabled", "False") == "True"
	
	text = config_parameter.sudo().get_param("web.base.sorturl", "")
	base_sorturl[0] = text if (enabled and text) else 'odoo'

	_logger.info("Generating routing map for key %s. URL Prefix: %s", str(key), base_sorturl[0])

	registry = Registry(threading.current_thread().dbname)
	installed = registry._init_modules.union(odoo.conf.server_wide_modules)
	mods = sorted(installed)
	routing_map = werkzeug.routing.Map(strict_slashes=False, converters=self._get_converters())
	for url, endpoint in self._generate_routing_rules(mods, converters=self._get_converters()):
		if base_sorturl[0] != 'odoo':
			# Rewrite all /odoo routes to /replacement
			url = re.sub(r'^/odoo(?=/|$)', '/' + base_sorturl[0], url)
		
		routing = submap(endpoint.routing, ROUTING_KEYS)
		if routing['methods'] is not None and 'OPTIONS' not in routing['methods']:
			routing['methods'] = routing['methods'] + ['OPTIONS']
		rule = FasterRule(url, endpoint=endpoint, **routing)
		rule.merge_slashes = False
		routing_map.add(rule)
	return routing_map


IrHttp.routing_map = routing_map


