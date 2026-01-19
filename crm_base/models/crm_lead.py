import re
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

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
		records = super().create(vals_list)

		for record in records:
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


	def action_mark_cold(self):
		for lead in self:
			lead.active = False


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