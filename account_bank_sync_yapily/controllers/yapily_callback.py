from odoo import http, _
from odoo.http import request
import requests
import requests.auth
import logging

_logger = logging.getLogger(__name__)

class YapilyController(http.Controller):

    @http.route('/yapily/callback', type='http', auth='user', website=True)
    def yapily_callback(self, **kw):
        consent_token = kw.get('consent')
        if not consent_token:
            return request.render('http_routing.http_error', {'status_code': _('400'), 'status_message': _('Missing Yapily Consent Token.')})
            
        company = request.env.company
        app_uuid = company.yapily_application_uuid
        secret = company.yapily_secret
        base_url = company.yapily_api_url or "https://api.yapily.com"

        # Find the journal that was recently attempting to connect.
        # Since this is a simple implementation, we assume the user was working on a specific journal.
        # Actually doing this robustly might involve passing the journal_id in the callback state param.
        
        journal = request.env['account.journal'].search([('yapily_institution_id', '!=', False)], limit=1, order='write_date desc')
        if journal:
            journal.yapily_consent_token = consent_token
            
            # Fetch available accounts to map
            auth = requests.auth.HTTPBasicAuth(app_uuid, secret)
            headers = {'Consent': consent_token}
            response = requests.get(f"{base_url}/accounts", headers=headers, auth=auth)
            
            accounts_data = []
            if response.status_code == 200:
                accounts_data = response.json().get('data', [])
                
            if accounts_data:
                # Automatically map the first active account for simplicity or if only one
                # Usually we'd redirect to a wizard to choose if len > 1
                journal.yapily_account_id = accounts_data[0].get('id')
                _logger.info("Successfully mapped Yapily account %s to Journal %s", journal.yapily_account_id, journal.id)
                
            return request.redirect('/web#action=account.action_account_journal_form&id=%s&model=account.journal&view_type=form' % journal.id)
            
        return request.render('http_routing.http_error', {'status_code': _('404'), 'status_message': _('No journal found pending Yapily connection.')})
