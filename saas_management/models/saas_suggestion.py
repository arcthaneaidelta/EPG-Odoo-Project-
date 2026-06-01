# -*- coding: utf-8 -*-
from odoo import models, fields

class SaasSuggestion(models.Model):
    _name = 'saas.suggestion'
    _description = 'Tenant Suggestion'
    _order = 'create_date desc'

    subscription_id = fields.Many2one('saas.subscription', string='Subscription', ondelete='cascade')
    database_name = fields.Char(related='subscription_id.database_name', string='Database', store=True)
    customer_id = fields.Many2one(related='subscription_id.partner_id', string='Customer', store=True)
    email = fields.Char(string='Sender Email', required=True)
    suggestion_text = fields.Text(string='Suggestion', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved')
    ], string='Status', default='new', tracking=True)
