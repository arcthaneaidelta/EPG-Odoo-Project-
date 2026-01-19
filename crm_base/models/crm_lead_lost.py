from odoo import models, fields
from odoo.tools import is_html_empty
from markupsafe import Markup
from odoo.tools.translate import _

class CrmLeadLost(models.TransientModel):
	_inherit = 'crm.lead.lost'
	
	# Add char field to replace Many2one
	lost_reason_text = fields.Char(string='Lost Reason', required=True)
	
	def action_lost_reason_apply(self):
		self.ensure_one()

		active_ids = self.env.context.get('active_ids', [])
		leads = self.env['crm.lead'].browse(active_ids)

		if not leads:
			return False

		if not is_html_empty(self.lost_feedback):
			leads._track_set_log_message(
				Markup(
					'<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>'
				) % (_('Lost Comment'), self.lost_feedback)
			)

		# Mark as lost
		leads.action_set_lost(
			lost_reason_id=self.lost_reason_id.id if self.lost_reason_id else False
		)

		# Write your custom field
		leads.write({
			'lost_reason_text': self.lost_reason_text
		})

		return True
