from odoo.addons.web.controllers.home import Home
from odoo.http import request, route
from ..models.home import _get_replacement_text

class CustomHome(Home):
    def _login_redirect(self, uid, redirect=None):
        url = super()._login_redirect(uid, redirect)
        replacement = _get_replacement_text(request.env)
        
        # Odoo 18 by default redirects to /odoo
        # So we force the rewrite to whatever the replacement is configured to be
        if url == '/odoo' and replacement != 'odoo':
            url = f'/{replacement}/'
            
        return url

    @route()
    def index(self, *args, **kw):
        response = super().index(*args, **kw)
        replacement = _get_replacement_text(request.env)
        if hasattr(response, 'status_code') and response.status_code in (301, 302, 303) and hasattr(response, 'location') and response.location.endswith('/odoo') and replacement != 'odoo':
            response.location = response.location.replace('/odoo', f'/{replacement}')
        return response
        
    def _web_client_readonly(self):
        return False

    @route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'], type='http', auth="none", readonly=_web_client_readonly)
    def web_client(self, s_action=None, **kw):
        replacement = _get_replacement_text(request.env)
        # If user directly accessed /odoo or /web and replacement is active, redirect them
        if request.httprequest.path in ('/odoo', '/web', '/odoo/') and replacement != 'odoo':
            return request.redirect(f'/{replacement}/')
        return super().web_client(s_action, **kw)
