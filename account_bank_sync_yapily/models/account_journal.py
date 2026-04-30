from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    yapily_institution_id = fields.Char(string='Yapily Institution ID', copy=False)
    yapily_account_id = fields.Char(string='Yapily Account ID', copy=False)
    yapily_consent_token = fields.Char(string='Yapily Consent Token', copy=False)
    yapily_consent_expiry = fields.Datetime(string='Yapily Consent Expiry', copy=False)
    yapily_last_sync_date = fields.Datetime(string='Last Sync Date', copy=False)

    def action_connect_yapily(self):
        self.ensure_one()
        return {
            'name': _('Connect Yapily Bank'),
            'type': 'ir.actions.act_window',
            'res_model': 'yapily.connect.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_journal_id': self.id},
        }

    def action_manual_yapily_sync(self):
        self.ensure_one()
        if not self.yapily_consent_token or not self.yapily_account_id:
            raise UserError(_('Please connect to Yapily first.'))
        company = self.env.company
        app_uuid = company.yapily_application_uuid
        secret = company.yapily_secret
        base_url = company.yapily_api_url or "https://api.yapily.com"
        
        # Call directly so UserExceptions are shown to the user
        self.env['account.bank.statement']._sync_journal_yapily(self, app_uuid, secret, base_url)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Started'),
                'message': _('Yapily Synchronization completed successfully for %s.') % self.name,
                'sticky': False,
            }
        }
