from odoo import models, fields, api

class CrmFileTask(models.Model):
    _name = 'crm.file.task'
    _description = 'File Task'
    _inherit = ['mail.thread']

    name = fields.Char('Task Summary', required=True, tracking=True)
    file_id = fields.Many2one('crm.file', string='File', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Assignee', tracking=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='pending', required=True, tracking=True)
    description = fields.Html('Description', tracking=True)
    document_ids = fields.Many2many('dms.file', 'crm_task_dms_file_rel', 'task_id', 'dms_file_id', string='Documents', tracking=True)

    def write(self, vals):
        if 'state' in vals:
            for record in self:
                record.file_id.message_post(body=f"Task '{record.name}' status changed to: {vals['state']}")
        
        res = super().write(vals)
        
        if 'user_id' in vals and vals['user_id']:
            user = self.env['res.users'].browse(vals['user_id'])
            for record in self:
                record.file_id.message_subscribe(partner_ids=[user.partner_id.id])
                record.file_id.message_post(
                    body=f"You have been assigned to Sub-Task: '{record.name}'",
                    partner_ids=[user.partner_id.id]
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                record.file_id.message_subscribe(partner_ids=[record.user_id.partner_id.id])
                record.file_id.message_post(
                    body=f"New Sub-Task created and assigned to you: '{record.name}'",
                    partner_ids=[record.user_id.partner_id.id]
                )
            else:
                record.file_id.message_post(body=f"New Task created: '{record.name}'")
        return records
