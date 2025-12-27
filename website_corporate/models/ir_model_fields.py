# models/ir_model_fields.py
from odoo import models

class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def formbuilder_whitelist(self, model_name):
        res = super().formbuilder_whitelist(model_name)
        if model_name == 'crm.lead':
            res.append('source_type')
        return res