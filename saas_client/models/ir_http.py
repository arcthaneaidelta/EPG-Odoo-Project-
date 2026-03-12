# # -*- coding: utf-8 -*-
# from odoo import models
# from odoo.http import request
# from werkzeug.utils import redirect

# class IrHttp(models.AbstractModel):
#     _inherit = 'ir.http'

#     @classmethod
#     def _dispatch(cls, endpoint):
#          # Check subscription status
#          # Only check on web requests (not static, not longpolling)
#          if hasattr(request, 'httprequest') and request.httprequest.path.startswith('/web') and not request.httprequest.path.startswith('/web/static'):
            
#              # Get status from config
#              # Use sudo() because user might not be logged in yet or have access
#              status = request.env['ir.config_parameter'].sudo().get_param('saas.subscription_status', 'active')
            
#              if status == 'suspended':
#                  # Get Manager URL
#                  manager_url = request.env['ir.config_parameter'].sudo().get_param('saas.manager_url')
                 
#                  if manager_url:
#                       # Redirect to Manager Portal Login
#                       return redirect(f"{manager_url}/web/login?suspended=1")
#                  else:
#                       # Fallback if no manager URL set - maybe show a simple error page?
#                       # For now, just let them be, or redirect to a local info page if we had one.
#                       pass
         
#          return super(IrHttp, cls)._dispatch(endpoint)

# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
from werkzeug.utils import redirect
import logging

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Override _dispatch to safely check subscription status on web requests."""
        try:
            # Only check web (website) requests, skip backend and static assets
            if hasattr(request, 'httprequest'):
                path = request.httprequest.path

                # 1. Block access to specific removed menus via URL
                restricted_paths = ['/odoo/apps', '/odoo/website', '/web/apps', '/web/website']
                if any(path == p or path.startswith(p + '/') for p in restricted_paths):
                    return redirect('/web')

                # 2. Prevent Debug mode in URL
                if 'debug' in request.httprequest.args:
                    query_args = request.httprequest.args.copy()
                    query_args.pop('debug', None)
                    from werkzeug.urls import url_encode
                    qs = url_encode(query_args)
                    new_url = path + ('?' + qs if qs else '')
                    # Disable active debug in session if present
                    if hasattr(request, 'session') and getattr(request.session, 'debug', False):
                        request.session.debug = ''
                    return redirect(new_url)

                # Ensure debug is off even if not in URL but in session
                if hasattr(request, 'session') and getattr(request.session, 'debug', False):
                    request.session.debug = ''

                if path.startswith('/') and not path.startswith('/web/static'):

                    # Fetch subscription status from config parameter
                    status = request.env['ir.config_parameter'].sudo().get_param(
                        'saas.subscription_status', 'active'
                    )

                    # Only redirect if status is suspended
                    if status == 'suspended':
                        if not path.startswith('/suspended'):
                            return redirect('/suspended')

        except Exception as e:
            # Log errors but DO NOT block request
            _logger.warning(f"Safe _dispatch: subscription check failed: {e}")

        # Always call original dispatch
        return super(IrHttp, cls)._dispatch(endpoint)
