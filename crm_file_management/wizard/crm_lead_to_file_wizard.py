from odoo import models, fields, api, _

class CrmLeadToFileWizard(models.TransientModel):
    _name = 'crm.lead.to.file.wizard'
    _description = 'Wizard to create Case File from Lead'

    lead_id = fields.Many2one('crm.lead', string='Opportunity', required=True)
    partner_id = fields.Many2one('res.partner', string='Client', related='lead_id.partner_id', readonly=True)
    type_id = fields.Many2one('crm.file.type', string='Workspace', required=True)
    name = fields.Char('File Name', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            lead = self.env['crm.lead'].browse(self.env.context.get('active_id'))
            res.update({
                'lead_id': lead.id,
                'name': _('File for %s') % (lead.partner_id.name if lead.partner_id else lead.name),
            })
        return res

    def action_create_file(self):
        self.ensure_one()
        file_vals = {
            'name': self.name,
            'lead_id': self.lead_id.id,
            'partner_id': self.partner_id.id,
            'type_id': self.type_id.id,
        }
        new_file = self.env['crm.file'].create(file_vals)
        return {
            'name': _('Case File'),
            'view_mode': 'form',
            'res_model': 'crm.file',
            'res_id': new_file.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
