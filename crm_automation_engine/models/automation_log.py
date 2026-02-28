# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import calendar
import logging

_logger = logging.getLogger(__name__)


class AutomationLog(models.Model):
    """
    Central audit log for all CRM automations.
    Every automation writes a record here with its trigger, action, and result.
    Records CANNOT be deleted (critical rule from requirements).
    """
    _name = 'automation.log'
    _description = 'CRM Automation Log'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char('Description', required=True, readonly=True)
    automation_type = fields.Selection([
        ('lead', 'Lead'),
        ('sale', 'Sale'),
        ('invoice', 'Invoice'),
        ('client', 'Client'),
        ('temporal', 'Temporal'),
    ], string='Type', required=True, readonly=True, index=True)
    trigger_event = fields.Selection([
        # Lead events
        ('lead_cold', 'Lead Cold (No Contact)'),
        ('lead_converted', 'Lead Converted to Client'),
        # Sale events
        ('quote_created', 'Quote Created'),
        ('quote_sent', 'Quote Sent'),
        ('quote_accepted', 'Quote Accepted'),
        ('quote_rejected', 'Quote Rejected'),
        # Invoice events
        ('order_confirmed', 'Order Confirmed'),
        ('invoice_generated', 'Invoice Generated'),
        ('invoice_sent', 'Invoice Sent'),
        ('invoice_overdue', 'Invoice Overdue'),
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_unpaid', 'Invoice Unpaid'),
        # Client events
        ('client_inactive', 'Client Inactive'),
        # Temporal events
        ('month_start', 'Start of Month'),
        ('month_end', 'End of Month'),
        ('quarter_start', 'Start of Quarter'),
        ('quarter_end', 'End of Quarter'),
    ], string='Trigger Event', required=True, readonly=True, index=True)
    model_name = fields.Char('Model', readonly=True)
    record_ref = fields.Char('Record Reference', readonly=True,
                             help='Format: model_name,record_id')
    action_taken = fields.Text('Action Taken', readonly=True)
    result = fields.Selection([
        ('success', 'Success'),
        ('fail', 'Failed'),
    ], string='Result', default='success', readonly=True, index=True)
    error_message = fields.Text('Error Details', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        readonly=True, index=True
    )

    # ─── CRITICAL RULE: No automation can delete data ───
    def unlink(self):
        raise UserError(_('Automation logs cannot be deleted. This is a system policy.'))

    # ─── Helper method for easy logging from automation code blocks ───
    @api.model
    def log_automation(self, name, automation_type, trigger_event,
                       model_name=False, record_id=False,
                       action_taken='', result='success',
                       error_message=False, company_id=False):
        """
        Convenience method called from base.automation code blocks.
        Creates an audit log record.
        """
        vals = {
            'name': name,
            'automation_type': automation_type,
            'trigger_event': trigger_event,
            'model_name': model_name or '',
            'record_ref': '%s,%s' % (model_name, record_id) if model_name and record_id else '',
            'action_taken': action_taken,
            'result': result,
            'error_message': error_message or '',
            'company_id': company_id or self.env.company.id,
        }
        try:
            return self.sudo().create(vals)
        except Exception as e:
            _logger.error('Failed to write automation log: %s', str(e))
            return self.browse()  # Return empty recordset on failure

    # ─── CRON: Client Inactive X Days ───
    @api.model
    def _cron_client_inactive(self):
        """
        Daily cron that finds customers with no sale orders or invoices
        in the last X days and creates alert activities.
        """
        companies = self.env['res.company'].search([
            ('enable_client_inactive_alert', '=', True)
        ])
        for company in companies:
            days = company.client_inactive_days or 30
            cutoff_date = date.today() - timedelta(days=days)

            # Find customers with no recent sale orders or invoices
            partners = self.env['res.partner'].sudo().search([
                ('customer_rank', '>', 0),
                ('active', '=', True),
                ('company_id', 'in', [company.id, False]),
            ])

            for partner in partners:
                # Check for recent activity
                recent_order = self.env['sale.order'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('date_order', '>=', cutoff_date),
                    ('company_id', '=', company.id),
                ], limit=1)

                recent_invoice = self.env['account.move'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('invoice_date', '>=', cutoff_date),
                    ('move_type', '=', 'out_invoice'),
                    ('company_id', '=', company.id),
                ], limit=1)

                if not recent_order and not recent_invoice:
                    # Check if we already created an alert recently
                    existing_activity = self.env['mail.activity'].sudo().search([
                        ('res_model', '=', 'res.partner'),
                        ('res_id', '=', partner.id),
                        ('summary', 'ilike', 'Inactive client'),
                        ('date_deadline', '>=', date.today() - timedelta(days=7)),
                    ], limit=1)

                    if not existing_activity:
                        try:
                            # Create alert activity
                            user_id = partner.user_id.id or company.partner_id.user_id.id or self.env.ref('base.user_admin').id
                            partner.activity_schedule(
                                'mail.mail_activity_data_todo',
                                summary=_('Inactive client — no activity in %s days') % days,
                                note=_('This customer has had no sale orders or invoices in the last %s days. Consider reaching out.') % days,
                                user_id=user_id,
                                date_deadline=date.today() + timedelta(days=3),
                            )
                            self.log_automation(
                                name='Client Inactive Alert: %s' % partner.name,
                                automation_type='client',
                                trigger_event='client_inactive',
                                model_name='res.partner',
                                record_id=partner.id,
                                action_taken='Created follow-up activity for inactive client (%s days)' % days,
                                company_id=company.id,
                            )
                        except Exception as e:
                            self.log_automation(
                                name='Client Inactive Alert Failed: %s' % partner.name,
                                automation_type='client',
                                trigger_event='client_inactive',
                                model_name='res.partner',
                                record_id=partner.id,
                                action_taken='Failed to create activity',
                                result='fail',
                                error_message=str(e),
                                company_id=company.id,
                            )

    # ─── CRON: Start of Month ───
    @api.model
    def _cron_start_of_month(self):
        """Runs daily. If today is the 1st, logs the temporal event."""
        today = date.today()
        if today.day != 1:
            return

        companies = self.env['res.company'].search([
            ('enable_temporal_automations', '=', True)
        ])
        for company in companies:
            self.log_automation(
                name='Start of Month: %s' % today.strftime('%B %Y'),
                automation_type='temporal',
                trigger_event='month_start',
                action_taken='Monthly start event triggered for %s' % today.strftime('%B %Y'),
                company_id=company.id,
            )
            _logger.info('Temporal event: Start of Month — %s (Company: %s)', today.strftime('%B %Y'), company.name)

    # ─── CRON: End of Month ───
    @api.model
    def _cron_end_of_month(self):
        """Runs daily. If today is the last day of the month, logs the event."""
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        if today.day != last_day:
            return

        companies = self.env['res.company'].search([
            ('enable_temporal_automations', '=', True)
        ])
        for company in companies:
            self.log_automation(
                name='End of Month: %s' % today.strftime('%B %Y'),
                automation_type='temporal',
                trigger_event='month_end',
                action_taken='Monthly end event triggered for %s' % today.strftime('%B %Y'),
                company_id=company.id,
            )
            _logger.info('Temporal event: End of Month — %s (Company: %s)', today.strftime('%B %Y'), company.name)

    # ─── CRON: Start of Quarter ───
    @api.model
    def _cron_start_of_quarter(self):
        """Runs daily. If today is Jan 1, Apr 1, Jul 1, or Oct 1, logs event."""
        today = date.today()
        quarter_starts = [(1, 1), (4, 1), (7, 1), (10, 1)]
        if (today.month, today.day) not in quarter_starts:
            return

        quarter_num = (today.month - 1) // 3 + 1
        companies = self.env['res.company'].search([
            ('enable_temporal_automations', '=', True)
        ])
        for company in companies:
            self.log_automation(
                name='Start of Q%s %s' % (quarter_num, today.year),
                automation_type='temporal',
                trigger_event='quarter_start',
                action_taken='Quarterly start event triggered for Q%s %s' % (quarter_num, today.year),
                company_id=company.id,
            )
            _logger.info('Temporal event: Start of Q%s %s (Company: %s)', quarter_num, today.year, company.name)

    # ─── CRON: End of Quarter ───
    @api.model
    def _cron_end_of_quarter(self):
        """Runs daily. If today is Mar 31, Jun 30, Sep 30, or Dec 31, logs event."""
        today = date.today()
        quarter_ends = [
            (3, 31), (6, 30), (9, 30), (12, 31)
        ]
        if (today.month, today.day) not in quarter_ends:
            return

        quarter_num = (today.month - 1) // 3 + 1
        companies = self.env['res.company'].search([
            ('enable_temporal_automations', '=', True)
        ])
        for company in companies:
            self.log_automation(
                name='End of Q%s %s' % (quarter_num, today.year),
                automation_type='temporal',
                trigger_event='quarter_end',
                action_taken='Quarterly end event triggered for Q%s %s' % (quarter_num, today.year),
                company_id=company.id,
            )
            _logger.info('Temporal event: End of Q%s %s (Company: %s)', quarter_num, today.year, company.name)
