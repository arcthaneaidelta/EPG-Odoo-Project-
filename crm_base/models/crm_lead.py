import re
from odoo import models, fields, api

class CrmLeadInherit(models.Model):
	_inherit = "crm.lead"

	# 1. New Fields [cite: 109-113]
	score = fields.Integer(compute="_compute_score", store=True, string="Score")
	source_type = fields.Selection(
		[("web", "Web"), ("manual", "Manual"), ("campaign", "Campaign")],
		string="Source Type",
		default="manual"
	)

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
		return records

	def write(self, vals):
		res = super().write(vals)
		if 'source_type' in vals:
			self._route_lead()
		return res

	def _route_lead(self):
		for lead in self:
			if lead.source_type == "web":
				team = self.env['crm.team'].search([('name', 'ilike', 'Website')], limit=1)
				if team:
					lead.team_id = team.id


	def action_mark_cold(self):
		for lead in self:
			lead.active = False

	# # 6. WhatsApp Integration 
	# def action_whatsapp_msg(self):
	#     self.ensure_one()
	#     if not self.phone:
	#         return
			
	#     msg = "Hello, following up on your inquiry."
	#     return {
	#         "type": "ir.actions.act_url",
	#         "url": f"https://wa.me/{self.phone}?text={msg}",
	#         "target": "new",
	#     }

	# def action_whatsapp(self):
	# 	self.ensure_one()
	# 	phone = self.partner_id.mobile or self.partner_id.phone
	# 	if not phone:
	# 		return False

	# 	message = f"Hello {self.partner_id.name}, regarding your inquiry."
	# 	url = f"https://wa.me/{phone}?text={message}"
	# 	print('/rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr')
	# 	print(message)
	# 	print(url)

	# 	return {
	# 		"type": "ir.actions.act_url",
	# 		"url": url,
	# 		"target": "new",
	# 	}

	def action_whatsapp(self):
		self.ensure_one()
		
		# 1. Get the raw phone number
		raw_phone = self.partner_id.mobile or self.partner_id.phone
		if not raw_phone:
			return False
		clean_phone = re.sub(r'[^0-9]', '', raw_phone)

		message = f"Hello {self.partner_id.name}, regarding your inquiry."
		url = f"https://wa.me/{clean_phone}?text={message}"
		return {
			"type": "ir.actions.act_url",
			"url": url,
			"target": "new",
		}