from odoo import models, fields, api
from datetime import datetime, timedelta

class CrmHealthReport(models.Model):
	_name = 'crm.health.report'
	_description = 'Business Health Report'

	company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
	
	# Metrics
	unpaid_invoices_count = fields.Integer(string='Unpaid Invoices')
	unpaid_invoices_amount = fields.Monetary(string='Unpaid Amount', currency_field='currency_id')
	leads_no_followup_count = fields.Integer(string='Leads without Follow-up')
	bank_unreconciled_count = fields.Integer(string='Unreconciled Bank Lines')
	pending_fiscal_models_count = fields.Integer(string='Pending Fiscal Models')
	overdue_sales_activity_count = fields.Integer(string='Overdue Sales Activities')
	
	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

	health_status = fields.Selection([
		('healthy', 'Healthy 🟢'),
		('attention', 'Attention 🟡'),
		('risk', 'Risk 🔴')
	], string='Status', default='healthy', required=True)
	
	last_calculated = fields.Date(string='Last Calculated')

	def action_calculate_health(self):
		"""Calculate the business health metrics for the company."""
		for record in self:
			today = fields.Date.today()
			company = record.company_id

			# 1. Unpaid Invoices (Customer Invoices past due)
			invoices = self.env['account.move'].search([
				('company_id', '=', company.id),
				('move_type', '=', 'out_invoice'),
				('state', '=', 'posted'),
				('payment_state', 'in', ('not_paid', 'partial')),
				('invoice_date_due', '<', today)
			])
			record.unpaid_invoices_count = len(invoices)
			record.unpaid_invoices_amount = sum(invoices.mapped('amount_residual'))

			# 2. Leads without follow-up (Leads with no scheduled activities)
			# Find leads that have NO activities
			leads = self.env['crm.lead'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
                ('activity_ids', '=', False)
            ])
			record.leads_no_followup_count = len(leads)

			# 3. Bank reconciliation
			# Bank statement lines not reconciled
			if 'account.bank.statement.line' in self.env:
				bank_lines = self.env['account.bank.statement.line'].search([
					('company_id', '=', company.id),
					('is_reconciled', '=', False)
				])
				record.bank_unreconciled_count = len(bank_lines)

			# 4. Pending fiscal models (if l10n_es_aeat is installed)
			pending_models = 0
			if 'l10n_es_aeat.report' in self.env:
				pending_models = self.env['l10n_es_aeat.report'].search_count([
					('company_id', '=', company.id),
					('state', 'in', ('draft', 'calculated'))
				])
			record.pending_fiscal_models_count = pending_models

			# 5. Overdue sales activity
			company_leads = self.env['crm.lead'].search([
				('company_id', '=', company.id)
			])

			overdue_activities = self.env['mail.activity'].search([
				('res_model', '=', 'crm.lead'),
				('res_id', 'in', company_leads.ids),
				('date_deadline', '<', today)
			])
			record.overdue_sales_activity_count = len(overdue_activities)

			# Evaluate Status
			status = 'healthy'
			
			# Risk Thresholds
			if (record.unpaid_invoices_count > 20 or 
				record.leads_no_followup_count > 50 or 
				record.bank_unreconciled_count > 100 or 
				record.pending_fiscal_models_count > 0 or 
				record.overdue_sales_activity_count > 50):
				status = 'risk'
			# Attention Thresholds
			elif (record.unpaid_invoices_count > 5 or 
				  record.leads_no_followup_count > 10 or 
				  record.bank_unreconciled_count > 20 or 
				  record.overdue_sales_activity_count > 10):
				status = 'attention'
				
			record.health_status = status
			record.last_calculated = fields.Datetime.now()

	@api.model
	def _cron_calculate_health(self):
		"""Cron job to calculate daily health index"""
		companies = self.env['res.company'].search([])
		for company in companies:
			report = self.search([('company_id', '=', company.id)], limit=1)
			if not report:
				report = self.create({'company_id': company.id})
			report.action_calculate_health()

	# --- Navigation Actions ---
	def action_view_unpaid_invoices(self):
		return {
			'name': 'Unpaid Invoices',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_mode': 'list,form',
			'domain': [
				('company_id', '=', self.company_id.id),
				('move_type', '=', 'out_invoice'),
				('state', '=', 'posted'),
				('payment_state', 'in', ('not_paid', 'partial')),
				('invoice_date_due', '<', fields.Date.today())
			],
		}

	def action_view_leads_no_followup(self):
		return {
			'name': 'Leads Without Follow-up',
			'type': 'ir.actions.act_window',
			'res_model': 'crm.lead',
			'view_mode': 'list,form',
			'domain': [
				('company_id', '=', self.company_id.id),
				('type', '=', 'lead'),
				('active', '=', True),
				('activity_ids', '=', False)
			],
		}

	def action_view_bank_reconciliation(self):
		return {
			'name': 'Unreconciled Bank Lines',
			'type': 'ir.actions.act_window',
			'res_model': 'account.bank.statement.line',
			'view_mode': 'list,form',
			'domain': [
				('company_id', '=', self.company_id.id),
				('is_reconciled', '=', False)
			],
		}

	def action_view_overdue_activities(self):
		return {
			'name': 'Overdue Sales Activities',
			'type': 'ir.actions.act_window',
			'res_model': 'mail.activity',
			'view_mode': 'list,form',
			'domain': [
				('res_model', '=', 'crm.lead'),
				('res_id', 'in', self.env['crm.lead'].search([
					('company_id', '=', self.company_id.id)
				]).ids),
				('date_deadline', '<', fields.Date.today())
			],
		}
