from odoo import models

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _get_default_action(self):
        return self.env.ref('crm_dashboard.action_crm_dashboard')