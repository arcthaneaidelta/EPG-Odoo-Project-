from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_percentage = fields.Float(
        string="Commission (%)",
        compute="_compute_commission_percentage",
        store=True
    )
    commission_amount = fields.Monetary('Commissiuon Amount', compute="_compute_commission_amount")

    @api.depends('user_id.commission_percentage', 'user_id.is_sales_representative')
    def _compute_commission_percentage(self):
        for order in self:
            if order.user_id and order.user_id.is_sales_representative:
                order.commission_percentage = order.user_id.commission_percentage
            else:
                order.commission_percentage = 0.0

    @api.depends('amount_total', 'commission_percentage')
    def _compute_commission_amount(self):
        for order in self:
            order.commission_amount = order.amount_total * (order.commission_percentage / 100.0)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.opportunity_id and order.opportunity_id.active:
                order.opportunity_id.action_set_won()
        return res
