from odoo import models, fields

class CrmFileStage(models.Model):
    _name = 'crm.file.stage'
    _description = 'File Phase'
    _order = 'sequence, id'

    name = fields.Char('Phase Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    fold = fields.Boolean('Folded in Kanban')
    type_id = fields.Many2one('crm.file.type', string='Workspace', ondelete='cascade')
