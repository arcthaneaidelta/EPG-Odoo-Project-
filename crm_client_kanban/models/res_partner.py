# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Total confirmed/done sale order amounts ──────────────────────────────
    kanban_total_sales = fields.Monetary(
        string='Total Sales',
        compute='_compute_kanban_stats',
        store=False,
        currency_field='currency_id',
    )

    # ── Invoice (customer) count ─────────────────────────────────────────────
    kanban_invoice_count = fields.Integer(
        string='Total Invoices',
        compute='_compute_kanban_stats',
        store=False,
    )
    kanban_invoice_count_month = fields.Integer(
        string='Invoices This Month',
        compute='_compute_kanban_stats',
        store=False,
    )

    # ── CRM phone calls / activities count ──────────────────────────────────
    kanban_call_count = fields.Integer(
        string='Total Calls',
        compute='_compute_kanban_stats',
        store=False,
    )
    kanban_call_count_month = fields.Integer(
        string='Calls This Month',
        compute='_compute_kanban_stats',
        store=False,
    )

    # ── Calendar meeting count ───────────────────────────────────────────────
    kanban_meeting_count = fields.Integer(
        string='Total Meetings',
        compute='_compute_kanban_stats',
        store=False,
    )
    kanban_meeting_count_month = fields.Integer(
        string='Meetings This Month',
        compute='_compute_kanban_stats',
        store=False,
    )

    # ── Sales growth trend (%) ───────────────────────────────────────────────
    kanban_sales_growth = fields.Float(
        string='Sales Growth %',
        compute='_compute_kanban_stats',
        store=False,
    )

    @api.depends('sale_order_ids', 'invoice_ids')
    def _compute_kanban_stats(self):
        today = fields.Date.today()
        first_day_this_month = today.replace(day=1)

        # First day of last month
        if today.month == 1:
            first_day_last_month = today.replace(year=today.year - 1, month=12, day=1)
            last_day_last_month = today.replace(month=1, day=1) - fields.Date.today().__class__.resolution
        else:
            first_day_last_month = today.replace(month=today.month - 1, day=1)
            last_day_last_month = first_day_this_month - fields.Date.today().__class__.resolution

        SaleOrder = self.env['sale.order']
        AccountMove = self.env['account.move']
        MailActivity = self.env['mail.activity']
        CalendarEvent = self.env['calendar.event']

        for partner in self:
            child_ids = partner.child_ids.ids + [partner.id]

            # ── Sales ────────────────────────────────────────────────────────
            sale_orders = SaleOrder.search([
                ('partner_id', 'in', child_ids),
                ('state', 'in', ['sale', 'done']),
            ])
            total_sales = sum(sale_orders.mapped('amount_total'))

            # Growth: compare this month vs last month
            sales_this_month = sum(
                sale_orders.filtered(
                    lambda o: o.date_order and o.date_order.date() >= first_day_this_month
                ).mapped('amount_total')
            )
            sales_last_month = sum(
                sale_orders.filtered(
                    lambda o: o.date_order and
                    first_day_last_month <= o.date_order.date() <= last_day_last_month
                ).mapped('amount_total')
            )
            if sales_last_month:
                growth = ((sales_this_month - sales_last_month) / sales_last_month) * 100
            else:
                growth = 0.0

            # ── Invoices ─────────────────────────────────────────────────────
            invoices = AccountMove.search([
                ('partner_id', 'in', child_ids),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '!=', 'cancel'),
            ])
            invoices_this_month = invoices.filtered(
                lambda i: i.invoice_date and i.invoice_date >= first_day_this_month
            )

            # ── Calls (mail.activity with call type, or crm activities) ──────
            calls = MailActivity.search([
                ('res_model', '=', 'res.partner'),
                ('res_id', 'in', child_ids),
                ('activity_type_id.category', '=', 'phonecall'),
            ])
            # Fallback: count all done activities tagged as calls via summary
            if not calls:
                calls = self.env['mail.activity'].search([
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', child_ids),
                    ('activity_type_id.name', 'ilike', 'call'),
                ])
            calls_this_month = calls.filtered(
                lambda c: c.date_deadline and c.date_deadline >= first_day_this_month
            )

            # ── Meetings ─────────────────────────────────────────────────────
            meetings = CalendarEvent.search([
                ('partner_ids', 'in', child_ids),
                ('start', '!=', False),
            ])
            meetings_this_month = meetings.filtered(
                lambda m: m.start and m.start.date() >= first_day_this_month
            )

            # ── Assign ───────────────────────────────────────────────────────
            partner.kanban_total_sales = total_sales
            partner.kanban_sales_growth = round(growth, 1)
            partner.kanban_invoice_count = len(invoices)
            partner.kanban_invoice_count_month = len(invoices_this_month)
            partner.kanban_call_count = len(calls)
            partner.kanban_call_count_month = len(calls_this_month)
            partner.kanban_meeting_count = len(meetings)
            partner.kanban_meeting_count_month = len(meetings_this_month)
