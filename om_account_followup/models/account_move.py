from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('followup.line', string="Nivel de Seguimiento")
    followup_date = fields.Date(string="Fecha de Seguimiento")
    result = fields.Float(compute='_get_result', string="Saldo Pendiente")

    def _get_result(self):
        for aml in self:
            aml.result = aml.debit - aml.credit
