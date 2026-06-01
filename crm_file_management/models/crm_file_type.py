from odoo import models, fields, api

class CrmFileType(models.Model):
    _name = 'crm.file.type'
    _description = 'File Workspace / Category'
    
    name = fields.Char('Workspace Name', required=True, translate=True)
    color = fields.Integer('Color Index')
    file_ids = fields.One2many('crm.file', 'type_id', string='Files')
    file_count = fields.Integer('File Count', compute='_compute_file_count')
    
    def _compute_file_count(self):
        for record in self:
            record.file_count = len(record.file_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Create default stages for each workspace
            self.env['crm.file.stage'].create([
                {'name': 'New', 'sequence': 10, 'type_id': record.id},
                {'name': 'In Progress', 'sequence': 20, 'type_id': record.id},
                {'name': 'Done', 'sequence': 30, 'type_id': record.id},
            ])
        return records
            
    def action_view_files(self):
        self.ensure_one()
        return {
            'name': 'Cases',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.file',
            'view_mode': 'kanban,list,form',
            'domain': [('type_id', '=', self.id)],
            'context': {'default_type_id': self.id},
        }
