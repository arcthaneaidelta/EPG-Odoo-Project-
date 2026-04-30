import requests
import requests.auth
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class YapilyConnectWizard(models.TransientModel):
    _name = 'yapily.connect.wizard'
    _description = 'Yapily Bank Connection Wizard'

    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    institution_id = fields.Char(string='Institution ID', required=True, help="E.g., xs2a-sandbox")
    
    def action_connect(self):
        self.ensure_one()
        company = self.env.company
        app_uuid = company.yapily_application_uuid
        secret = company.yapily_secret
        base_url = company.yapily_api_url or "https://api.yapily.com"

        if not app_uuid or not secret:
            raise UserError(_("Yapily Application UUID and Secret must be configured in Company Settings."))

        auth = requests.auth.HTTPBasicAuth(app_uuid, secret)
        
        # Odoo Callback URL
        callback_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/yapily/callback'
        
        payload = {
            "applicationUserId": f"odoo_user_{self.env.user.id}",
            "institutionId": self.institution_id,
            "callback": callback_url,
            "accountRequest": {
                "expiresAt": fields.Datetime.add(fields.Datetime.now(), days=90).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{base_url}/account-auth-requests", json=payload, headers=headers, auth=auth)
        
        if response.status_code not in (200, 201):
            raise UserError(_("Failed to create Yapily auth request: %s") % response.text)
            
        data = response.json().get('data', {})
        auth_url = data.get('authorisationUrl')
        
        if not auth_url:
            raise UserError(_("No authorisation URL found in Yapily response."))
            
        # Store temporary data in the journal to know what we are expecting back
        self.journal_id.yapily_institution_id = self.institution_id
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'self',
        }
