from odoo import models, fields, api

class CrmFileChecklist(models.Model):
    _name = 'crm.file.checklist'
    _description = 'File Checklist Item'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char('Item', required=True, tracking=True)
    file_id = fields.Many2one('crm.file', string='File', ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10, tracking=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ], string='Status', default='pending', required=True, tracking=True)
    attachment_ids = fields.Many2many('dms.file', 'crm_checklist_dms_file_rel', 'checklist_id', 'dms_file_id', string='Linked Documents', tracking=True)

    def action_toggle_state(self):
        for record in self:
            record.state = 'completed' if record.state == 'pending' else 'pending'

    def write(self, vals):
        if 'state' in vals:
            for record in self:
                record.file_id.message_post(body=f"Checklist item '{record.name}' status changed to: {vals['state']}")
        if 'name' in vals:
            for record in self:
                record.file_id.message_post(body=f"Checklist item renamed from '{record.name}' to '{vals['name']}'")
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.file_id.message_post(body=f"New Checklist item added: '{record.name}'")
        return records
