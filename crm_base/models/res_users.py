from odoo import models, api, fields, _
from markupsafe import Markup

class ResUsers(models.Model):
	_inherit = "res.users"

	referral_code = fields.Char(string="Sales Representative Code", copy=False, index=True)
	is_sales_representative = fields.Boolean(string="Is Sales Representative")
	commission_percentage = fields.Float(string="Commission (%)", default=10.0)
	sale_order_ids = fields.One2many("sale.order", "user_id", string="Referred Sales Orders")

	# Coverage fields for automatic assignment
	assigned_industry_ids = fields.Many2many('res.partner.industry', string='Assigned Sectors')
	assigned_state_ids = fields.Many2many('res.country.state', string='Assigned Regions')
	assigned_country_ids = fields.Many2many('res.country', string='Assigned Countries')
	
	company_currency_id = fields.Many2one(
		related='company_id.currency_id',
		string='Company Currency',
		readonly=True
	)
	
	total_commission_amount = fields.Monetary(
		string="Total Commission",
		compute="_compute_total_commission",
		currency_field='company_currency_id'
	)

	tour_enabled = fields.Boolean(default=False, compute='_compute_tour_enabled_epg', store=True, readonly=False)

	@api.depends('create_date')
	def _compute_tour_enabled_epg(self):
		for user in self:
			user.tour_enabled = False

	@api.model
	def _force_sync_signup_translations(self):
		template_ids = [
			self.env.ref('auth_signup.set_password_email', raise_if_not_found=False),
			self.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False),
		]
		langs = self.env['res.lang'].search([('active', '=', True)])
		
		for template in template_ids:
			if not template:
				continue
			base_html = template.with_context(lang='en_US').body_html
			base_subject = template.with_context(lang='en_US').subject
			if not base_html:
				continue
			
			for lang in langs:
				template.with_context(lang=lang.code).write({
					'body_html': base_html,
					'subject': base_subject,
				})

	@api.depends('sale_order_ids.commission_amount', 'sale_order_ids.state')
	def _compute_total_commission(self):
		for user in self:
			# Only count confirmed/done orders if needed, for now all referring orders
			confirmed_orders = user.sale_order_ids.filtered(lambda s: s.state in ('sale', 'done'))
			user.total_commission_amount = sum(confirmed_orders.mapped('commission_amount'))



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