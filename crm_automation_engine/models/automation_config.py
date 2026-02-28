# -*- coding: utf-8 -*-

from odoo import models, fields, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Lead Automations
    enable_lead_auto_assign = fields.Boolean("Auto-assign Sales Rep", default=True)
    enable_lead_auto_task = fields.Boolean("Create Contact 24h Task", default=True)
    enable_lead_auto_email = fields.Boolean("Send Lead Confirmation Email", default=True)
    enable_lead_cold_alert = fields.Boolean("Alert on Cold Leads", default=True)
    lead_cold_hours = fields.Integer("Cold Lead Hours", default=24)
    
    # 8.3 Correct CRM Use
    enable_lead_no_activity_alert = fields.Boolean("Alert: Leads w/o Logged Activities", default=True)
    lead_no_activity_days = fields.Integer("Lead No Activity Days", default=3)
    enable_stuck_opportunity_alert = fields.Boolean("Alert: Stuck Opportunities", default=True)
    opportunity_stuck_days = fields.Integer("Stuck Opportunity Days", default=14)
    enable_action_recommendations = fields.Boolean("Enable Action Recommendations", default=True)

    # 8.6 Team Control
    enable_opportunity_overload_alert = fields.Boolean("Alert: Opportunity Overload", default=True)
    opportunity_overload_threshold = fields.Integer("Opportunity Overload Threshold", default=50)
    enable_salesperson_inactivity_warning = fields.Boolean("Alert: Salesperson Inactivity", default=True)
    salesperson_inactivity_days = fields.Integer("Salesperson Inactivity Days", default=7)

    # Sale Automations
    enable_quote_followup = fields.Boolean("Create Quote Follow-up Task", default=True)
    quote_followup_days = fields.Integer("Quote Follow-up Days", default=3)
    enable_quote_confirmed_notify = fields.Boolean("Notify Rep on confirmation", default=True)
    
    # Invoice Automations
    enable_invoice_auto_send = fields.Boolean("Auto-send Invoice Email", default=True)
    enable_invoice_paid_notify = fields.Boolean("Notify on Payment", default=True)
    enable_invoice_overdue_alert = fields.Boolean("Alert on Overdue", default=True)
    
    # Client Automations
    enable_client_welcome_email = fields.Boolean("Send Client Welcome Email", default=True)
    enable_client_inactive_alert = fields.Boolean("Alert on Inactive Client", default=True)
    client_inactive_days = fields.Integer("Client Inactive Days", default=30)
    
    # Temporal Automations
    enable_temporal_events = fields.Boolean("Log Temporal Events (Month/Quarter)", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Lead
    enable_lead_auto_assign = fields.Boolean(related='company_id.enable_lead_auto_assign', readonly=False)
    enable_lead_auto_task = fields.Boolean(related='company_id.enable_lead_auto_task', readonly=False)
    enable_lead_auto_email = fields.Boolean(related='company_id.enable_lead_auto_email', readonly=False)
    enable_lead_cold_alert = fields.Boolean(related='company_id.enable_lead_cold_alert', readonly=False)
    lead_cold_hours = fields.Integer(related='company_id.lead_cold_hours', readonly=False)

    # 8.3 Correct CRM Use
    enable_lead_no_activity_alert = fields.Boolean(related='company_id.enable_lead_no_activity_alert', readonly=False)
    lead_no_activity_days = fields.Integer(related='company_id.lead_no_activity_days', readonly=False)
    enable_stuck_opportunity_alert = fields.Boolean(related='company_id.enable_stuck_opportunity_alert', readonly=False)
    opportunity_stuck_days = fields.Integer(related='company_id.opportunity_stuck_days', readonly=False)
    enable_action_recommendations = fields.Boolean(related='company_id.enable_action_recommendations', readonly=False)

    # 8.6 Team Control
    enable_opportunity_overload_alert = fields.Boolean(related='company_id.enable_opportunity_overload_alert', readonly=False)
    opportunity_overload_threshold = fields.Integer(related='company_id.opportunity_overload_threshold', readonly=False)
    enable_salesperson_inactivity_warning = fields.Boolean(related='company_id.enable_salesperson_inactivity_warning', readonly=False)
    salesperson_inactivity_days = fields.Integer(related='company_id.salesperson_inactivity_days', readonly=False)

    # Sale
    enable_quote_followup = fields.Boolean(related='company_id.enable_quote_followup', readonly=False)
    quote_followup_days = fields.Integer(related='company_id.quote_followup_days', readonly=False)
    enable_quote_confirmed_notify = fields.Boolean(related='company_id.enable_quote_confirmed_notify', readonly=False)

    # Invoice
    enable_invoice_auto_send = fields.Boolean(related='company_id.enable_invoice_auto_send', readonly=False)
    enable_invoice_paid_notify = fields.Boolean(related='company_id.enable_invoice_paid_notify', readonly=False)
    enable_invoice_overdue_alert = fields.Boolean(related='company_id.enable_invoice_overdue_alert', readonly=False)

    # Client
    enable_client_welcome_email = fields.Boolean(related='company_id.enable_client_welcome_email', readonly=False)
    enable_client_inactive_alert = fields.Boolean(related='company_id.enable_client_inactive_alert', readonly=False)
    client_inactive_days = fields.Integer(related='company_id.client_inactive_days', readonly=False)
    
    # Temporal
    enable_temporal_events = fields.Boolean(related='company_id.enable_temporal_events', readonly=False)
