from odoo import models, fields, api, _

class SignOcaTemplate(models.Model):
    _inherit = 'sign.oca.template'

    template_type = fields.Selection([
        ('contract', 'Contract'),
        ('budget', 'Budget'),
        ('invoice', 'Invoice'),
        ('email', 'Email')
    ], string='Template Type', default='contract', tracking=True)
