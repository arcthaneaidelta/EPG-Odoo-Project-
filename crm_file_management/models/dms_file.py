from odoo import models, fields

class DmsFile(models.Model):
    _inherit = 'dms.file'

    crm_task_ids = fields.Many2many(
        'crm.file.task',
        'crm_task_dms_file_rel',
        'dms_file_id',
        'task_id',
        string='Related CRM Tasks',
        readonly=True
    )
    crm_file_ids = fields.Many2many(
        'crm.file',
        'crm_file_dms_file_rel',
        'dms_file_id',
        'file_id',
        string='Related Case Files',
        readonly=True
    )
    crm_checklist_ids = fields.Many2many(
        'crm.file.checklist',
        'crm_checklist_dms_file_rel',
        'dms_file_id',
        'checklist_id',
        string='Related Checklists',
        readonly=True
    )
