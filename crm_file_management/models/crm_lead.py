from odoo import models, fields, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    file_ids = fields.One2many('crm.file', 'lead_id', string='Files', tracking=True,)
    file_count = fields.Integer(compute='_compute_file_count', string='File Count')

    def _compute_file_count(self):
        for lead in self:
            lead.file_count = len(lead.file_ids)

    def action_view_files(self):
        self.ensure_one()
        return {
            'name': _('Files'),
            'view_mode': 'kanban,list,form',
            'res_model': 'crm.file',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
            'type': 'ir.actions.act_window',
        }

    def action_create_file(self):
        self.ensure_one()
        return {
            'name': _('Create Case File'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.to.file.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
