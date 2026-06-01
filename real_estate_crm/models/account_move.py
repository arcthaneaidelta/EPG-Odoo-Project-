from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    rental_contract_id = fields.Many2one(
        'real.estate.rental.contract',
        string='Rental Contract',
        readonly=True,
        copy=False
    )
