from odoo import models, fields, api

class CrmFile(models.Model):
    _name = 'crm.file'
    _description = 'CRM File'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='File Name', required=True, tracking=True)
    type_id = fields.Many2one('crm.file.type', string='Workspace', tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Opportunity', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Client', related='lead_id.partner_id', store=True, readonly=False, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    stage_id = fields.Many2one('crm.file.stage', string='Phase', tracking=True, group_expand='_read_group_stage_ids', domain="[('type_id', '=', type_id)]")
    
    checklist_ids = fields.One2many('crm.file.checklist', 'file_id', string='Checklist')
    task_ids = fields.One2many('crm.file.task', 'file_id', string='Tasks')
    document_ids = fields.Many2many('dms.file', 'crm_file_dms_file_rel', 'file_id', 'dms_file_id', string='Documents')
    color = fields.Integer("Color Index")
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')], string='Status',
        copy=False, default='normal', required=True, tracking=True)
    date_last_stage_update = fields.Datetime(
        string='Last Stage Update',
        index=True,
        default=fields.Datetime.now,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'stage_id' in vals and 'date_last_stage_update' not in vals:
                vals['date_last_stage_update'] = fields.Datetime.now()
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                record.message_subscribe(partner_ids=[record.user_id.partner_id.id])
        return records

    def write(self, vals):
        if 'stage_id' in vals and 'date_last_stage_update' not in vals:
            for record in self:
                if record.stage_id.id != vals['stage_id']:
                    vals['date_last_stage_update'] = fields.Datetime.now()
                    break
        res = super().write(vals)
        if 'user_id' in vals and vals['user_id']:
            user = self.env['res.users'].browse(vals['user_id'])
            for record in self:
                record.message_subscribe(partner_ids=[user.partner_id.id])
                record.message_post(
                    body=f"You have been assigned as the Responsible for File: {record.name}",
                    partner_ids=[user.partner_id.id]
                )
        return res

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            stage = self.env['crm.file.stage'].search([('type_id', '=', self.type_id.id)], limit=1, order='sequence asc')
            if stage:
                self.stage_id = stage

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None, **kwargs):
        type_id = self.env.context.get('default_type_id') or self.env.context.get('active_id')
        if type_id:
            return self.env['crm.file.stage'].search([('type_id', '=', type_id)])
        return self.env['crm.file.stage'].search([])
