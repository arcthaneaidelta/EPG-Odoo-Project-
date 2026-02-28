from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_amount = fields.Monetary(
        string="Commission Amount",
        compute="_compute_commission_amount",
        store=True,
        currency_field='currency_id'
    )

    @api.depends('amount_total')
    def _compute_commission_amount(self):
        for order in self:
            order.commission_amount = order.amount_total * 0.10
