import re
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields

class ResCompany(models.Model):
	_inherit = 'res.company'

	# --- CRM Automations ---
	enable_lead_automation = fields.Boolean("Enable Lead Automation", default=True)


class CrmLeadInherit(models.Model):
	_inherit = "crm.lead"

	# 1. New Fields [cite: 109-113]
	score = fields.Integer(compute="_compute_score", store=True, string="Score")
	source_type = fields.Selection(
		[("web", "Web"), ("manual", "Manual"), ("campaign", "Campaign")],
		string="Source Type",
		default="manual"
	)
	sequence = fields.Integer(string='Sequence', default=10)
	visitor_name = fields.Char("Name")
	lost_reason_text = fields.Char(string='Lost Reason', readonly=True, copy=False)
	
	referral_code = fields.Char(string="Referral Code")
	referrer_user_id = fields.Many2one('res.users', string="Referrer")

	@api.depends("source_type", "partner_id")
	def _compute_score(self):
		for lead in self:
			score = 0
			if lead.source_type == "web":
				score += 10
			if lead.partner_id:
				score += 5
			lead.score = score


	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			if vals.get('referral_code'):
				referrer = self.env['res.users'].search([
					('referral_code', '=', vals['referral_code']),
					('is_sales_representative', '=', True)
				], limit=1)
				if referrer:
					vals['referrer_user_id'] = referrer.id
					vals['user_id'] = referrer.id  # Automatically assign lead to the rep

		records = super().create(vals_list)

		for record in records:
			if not record.referrer_user_id:  # Only route to generic web team if no rep explicitly assigned
				record._route_lead()
			# Send email notification for web leads
			record._send_lead_notification_email()

		return records

	def _send_lead_notification_email(self):
		"""Send email notification when a new lead is created from website"""
		for lead in self:
			# Only send for web source type (optional - remove if you want for all leads)
			if lead.source_type == 'web':
				try:
					# Get the email template
					template = self.env.ref(
						'crm_base.email_template_new_lead_notification',
						raise_if_not_found=False
					)
					if template:
						# Send the email
						template.send_mail(lead.id, force_send=True)
						_logger.info(f"Lead notification email sent for lead: {lead.name}")
					else:
						_logger.warning("Email template not found for lead notification")
				except Exception as e:
					_logger.error(f"Failed to send lead notification email: {str(e)}")

	def write(self, vals):
		res = super().write(vals)
		if 'source_type' in vals:
			self._route_lead()
		return res

	def _route_lead(self):
		for lead in self:
			if lead.source_type == "web":
				team = self.env['crm.team'].search([('name', '=', 'Website')], limit=1)
				if team:
					lead.team_id = team.id
					lead.user_id = team.user_id.id

			# if lead.user_id and lead.company_id.enable_lead_automation:
			# 	deadline = fields.Date.today() + timedelta(days=1)
			# 	lead.activity_schedule(
			# 		'mail.mail_activity_data_todo',
			# 		summary='🚀 New Lead: Contact within 24h',
			# 		note=f'Source: {lead.source_id.name or "Web"}',
			# 		user_id=lead.user_id.id,
			# 		date_deadline=deadline
			# 	)


	# def action_mark_cold(self):
	# 	for lead in self:
	# 		lead.active = False


	def action_whatsapp(self):
		self.ensure_one()
		
		# 1. Get the raw phone number
		raw_phone = self.partner_id.mobile or self.partner_id.phone or self.phone
		if not raw_phone:
			return False
		clean_phone = re.sub(r'[^0-9]', '', raw_phone)
		if self.partner_id:
			message = f"Hello {self.partner_id.name}, regarding your inquiry."
			url = f"https://wa.me/{clean_phone}?text={message}"
		else:
			message = f"Hello, regarding your inquiry."
			url = f"https://wa.me/{clean_phone}?text={message}"
		return {
			"type": "ir.actions.act_url",
			"url": url,
			"target": "new",
		}
	def _handle_partner_assignment(self, force_partner_id=False, create_missing=True):
		"""Override to pass referrer and client_type to new partner"""
		# Let the standard assignment run first
		partner_ids = super()._handle_partner_assignment(force_partner_id=force_partner_id, create_missing=create_missing)
		
		# If a new partner was created (or even an existing one linked), sync our new fields
		for lead in self:
			if lead.partner_id:
				vals = {}
				# Only overwrite if partner doesn't have it already
				if lead.referral_code and not lead.partner_id.referral_code:
					vals['referral_code'] = lead.referral_code
				if lead.referrer_user_id and not lead.partner_id.referrer_user_id:
					vals['referrer_user_id'] = lead.referrer_user_id.id
				# Standard Odoo salesperson sync
				if lead.user_id and not lead.partner_id.user_id:
					vals['user_id'] = lead.user_id.id
					
				if vals:
					lead.partner_id.write(vals)
					
		return partner_ids
