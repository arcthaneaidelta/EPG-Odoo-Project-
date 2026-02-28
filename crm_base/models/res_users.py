from odoo import models, api, fields, _
from markupsafe import Markup

class ResUsers(models.Model):
	_inherit = "res.users"

	referral_code = fields.Char(string="Sales Representative Code", copy=False, index=True)
	is_sales_representative = fields.Boolean(string="Is Sales Representative")
	sale_order_ids = fields.One2many("sale.order", "user_id", string="Referred Sales Orders")



	def _init_odoobot(self):
		self.ensure_one()

		odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
		channel = self.env['discuss.channel'].channel_get([odoobot_id, self.partner_id.id])

		message = Markup("%s<br/>%s<br/><b>%s</b> <span class=\"o_odoobot_command\">:)</span>") % (
			_("Hola,"),
			_("El chat de EPG ayuda a los empleados a colaborar de manera eficiente. Estoy aquí para ayudarte a descubrir sus funcionalidades."),
			_("Prueba enviarme un emoji")
		)

		channel.sudo().message_post(
			author_id=odoobot_id,
			body=message,
			message_type="comment",
			silent=True,
			subtype_xmlid="mail.mt_comment",
		)

		self.sudo().odoobot_state = 'onboarding_emoji'
		return channel