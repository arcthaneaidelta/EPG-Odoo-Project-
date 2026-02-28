# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rejection_reason = fields.Char(string="Rejection Reason", copy=False)
