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
		template_invite = self.env.ref('auth_signup.set_password_email', raise_if_not_found=False)
		template_signup = self.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
		
		langs = self.env['res.lang'].search([('active', '=', True)])
		
		invite_html = """
<table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #FFFFFF; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: #FFFFFF; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle">
                    <span style="font-size: 10px;">Bienvenido al portal</span><br/>
                    <span style="font-size: 20px; font-weight: bold;">
                        <t t-out="object.name or ''">Marc Demo</t>
                    </span>
                </td><td valign="middle" align="right" t-if="not object.company_id.uses_default_logo">
                    <img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.company_id.name"/>
                </td></tr>
                <tr><td colspan="2" style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Estimado/a <t t-out="object.name or ''">Marc Demo</t>,<br /><br />
                        Ha sido invitado/a por <t t-out="object.create_uid.name or ''">Admin</t> de <t t-out="object.company_id.name or ''">YourCompany</t> para conectarse a nuestro portal.
                        <div style="margin: 16px 0px 16px 0px;">
                            <a t-att-href="object.partner_id._get_signup_url()"
                                t-attf-style="background-color: {{object.company_id.email_secondary_color or '#005082'}}; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                                Aceptar invitación
                            </a>
                        </div>
                        <b> Este enlace será válido durante <t t-out="int(int(object.env['ir.config_parameter'].sudo().get_param('auth_signup.signup.validity.hours',144))/24)"></t> días </b> <br/>
                        Su correo electrónico de inicio de sesión es: <b><a t-attf-href="/web/login?login={{ object.email }}" target="_blank" t-out="object.email or ''">mark.brown23@example.com</a></b><br /><br />
                        ¡Esperamos que disfrute de la experiencia!<br />
                        --<br/>El equipo de <t t-out="object.company_id.name or 'EPG'">EPG</t>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="object.company_id.name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="object.company_id.phone or ''">+1 650-123-4567</t>
                    <t t-if="object.company_id.email">
                        | <a t-att-href="'mailto:%s' % object.company_id.email" style="text-decoration:none; color: #454748;" t-out="object.company_id.email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="object.company_id.website">
                        | <a t-att-href="'%s' % object.company_id.website" style="text-decoration:none; color: #454748;" t-out="object.company_id.website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
<tr><td align="center" style="min-width: 590px;">
    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
      <tr><td style="text-align: center; font-size: 13px;">
        Powered by <a target="_blank" href="https://eficienciayproductividadglobal.com" style="color: #005082;">EPG</a>
      </td></tr>
    </table>
</td></tr>
</table>
"""

		signup_html = """
<table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #FFFFFF; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: #FFFFFF; color: #454748; border-collapse:separate;">
<tbody>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle">
                    <span style="font-size: 10px;">Su Cuenta</span><br/>
                    <span style="font-size: 20px; font-weight: bold;">
                        <t t-out="object.name or ''">Marc Demo</t>
                    </span>
                </td><td valign="middle" align="right" t-if="not object.company_id.uses_default_logo">
                    <img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.company_id.name"/>
                </td></tr>
                <tr><td colspan="2" style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Estimado/a <t t-out="object.name or ''">Marc Demo</t>,<br/><br/>
                        Su cuenta ha sido creada exitosamente.<br/>
                        Su inicio de sesión es <strong><t t-out="object.email or ''">mark.brown23@example.com</t></strong><br/>
                        Para acceder a su cuenta, puede usar el siguiente enlace:
                        <div style="margin: 16px 0px 16px 0px;">
                            <a t-attf-href="/web/login?auth_login={{object.email}}"
                                style="background-color: #005082; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                                Ir a Mi Cuenta
                            </a>
                        </div>
                        Gracias,<br/>
                        <t t-if="user.signature">
                            <br/>
                            <t t-out="user.signature or ''">--<br/>Mitchell Admin</t>
                        </t>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="object.company_id.name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="object.company_id.phone or ''">+1 650-123-4567</t>
                    <t t-if="object.company_id.email">
                        | <a t-attf-href="mailto:{{object.company_id.email}}" style="text-decoration:none; color: #454748;" t-out="object.company_id.email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="object.company_id.website">
                        | <a t-att-href="object.company_id.website" style="text-decoration:none; color: #454748;" t-out="object.company_id.website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
<tr><td align="center" style="min-width: 590px;">
    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
      <tr><td style="text-align: center; font-size: 13px;">
        Powered by <a target="_blank" href="https://eficienciayproductividadglobal.com" style="color: #005082;">EPG</a>
      </td></tr>
    </table>
</td></tr>
</table>
"""

		if template_invite:
			template_invite.write({
				'body_html': invite_html,
				'subject': "{{ object.create_uid.name }} de {{ object.company_id.name }} le invita a conectarse al portal"
			})
			for lang in langs:
				template_invite.with_context(lang=lang.code).write({
					'body_html': invite_html,
					'subject': "{{ object.create_uid.name }} de {{ object.company_id.name }} le invita a conectarse al portal"
				})

		if template_signup:
			template_signup.write({
				'body_html': signup_html,
				'subject': "Bienvenido a {{ object.company_id.name }}!"
			})
			for lang in langs:
				template_signup.with_context(lang=lang.code).write({
					'body_html': signup_html,
					'subject': "Bienvenido a {{ object.company_id.name }}!"
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