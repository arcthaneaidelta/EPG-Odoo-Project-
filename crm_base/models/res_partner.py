from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import requests
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    client_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('freelancer', 'Freelancer'),
        ('sales_rep', 'Sales representative'),
        ('supplier', 'Supplier'),
        ('other', 'Others')
    ], string="Client Type")
    
    referrer_user_id = fields.Many2one('res.users', string="Referrer")
    referral_code = fields.Char(string="Referral Code")
    referral_code_used = fields.Char()

    company_type = fields.Selection(
        selection=[
            ("company", "Business"),
            ("person", "Private Person"),
        ]
    )
    date_of_birth = fields.Date(string="Date of Birth")
    nationality_id = fields.Many2one('res.country', string="Nationality")
    
    additional_email_ids = fields.One2many('res.partner.email', 'partner_id', string="Additional Emails")
    additional_phone_ids = fields.One2many('res.partner.phone', 'partner_id', string="Additional Phones")

    @api.onchange('zip')
    def _onchange_zip_spanish(self):
        if self.zip and self.country_id and self.country_id.code == 'ES':
            if not re.match(r'^\d{5}$', self.zip):
                return
            try:
                url = f"https://api.zippopotam.us/es/{self.zip}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    place = data.get('places', [{}])[0]
                    city = place.get('place name')
                    state_name = place.get('state')
                    if city:
                        self.city = city
                    if state_name:
                        state = self.env['res.country.state'].search([
                            ('name', '=ilike', state_name),
                            ('country_id', '=', self.country_id.id)
                        ], limit=1)
                        if state:
                            self.state_id = state
            except Exception as e:
                _logger.warning("Spanish ZIP Autocomplete failed: %s", e)

    @api.onchange('state_id')
    def _onchange_state_id_spanish(self):
        """If state is selected and country is Spain, pre-fill ZIP prefix if empty"""
        if self.state_id and self.country_id and self.country_id.code == 'ES' and not self.zip:
            if self.state_id.code and self.state_id.code.isdigit():
                self.zip = self.state_id.code + '000'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('user_id'):
                # Try to find a salesperson match based on coverage
                industry_id = vals.get('industry_id')
                state_id = vals.get('state_id')
                country_id = vals.get('country_id')
                
                matching_user = False
                
                # 1. Match Sector
                if industry_id:
                    matching_user = self.env['res.users'].search([
                        ('is_sales_representative', '=', True),
                        ('assigned_industry_ids', 'in', industry_id)
                    ], limit=1)
                
                # 2. Match Region
                if not matching_user and state_id:
                    matching_user = self.env['res.users'].search([
                        ('is_sales_representative', '=', True),
                        ('assigned_state_ids', 'in', state_id)
                    ], limit=1)
                
                # 3. Match Country
                if not matching_user and country_id:
                    matching_user = self.env['res.users'].search([
                        ('is_sales_representative', '=', True),
                        ('assigned_country_ids', 'in', country_id)
                    ], limit=1)
                
                if matching_user:
                    vals['user_id'] = matching_user.id

        partners = super(ResPartner, self).create(vals_list)
        template = self.env.ref('crm_base.email_template_welcome_new_customer', raise_if_not_found=False)
        for partner in partners:
            if partner.customer_rank > 0 and partner.email and template:
                template.send_mail(partner.id, force_send=True)
        return partners

class ResPartnerEmail(models.Model):
    _name = 'res.partner.email'
    _description = 'Additional Partner Email'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade')
    email = fields.Char(string="Email", required=True)
    note = fields.Char(string="Note")

class ResPartnerPhone(models.Model):
    _name = 'res.partner.phone'
    _description = 'Additional Partner Phone'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade')
    phone = fields.Char(string="Phone", required=True)
    note = fields.Char(string="Note")