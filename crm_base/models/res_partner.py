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

    @api.constrains('vat', 'country_id')
    def _check_vat_spanish_dni(self):
        for partner in self:
            if not partner.vat or not partner.country_id or partner.country_id.code != 'ES':
                continue
            
            # Clean VAT (remove spaces and dots)
            vat = partner.vat.strip().upper()
            if vat.startswith('ES'):
                vat = vat[2:]
            
            # DNI: 8 digits + 1 letter
            # NIE: X/Y/Z + 7 digits + 1 letter
            dni_pattern = re.compile(r'^[0-9]{8}[A-Z]$')
            nie_pattern = re.compile(r'^[XYZ][0-9]{7}[A-Z]$')
            
            if dni_pattern.match(vat) or nie_pattern.match(vat):
                mapping = "TRWAGMYFPDXBNJZSQVHLCKE"
                
                # Convert NIE prefix to digit
                if vat[0] == 'X':
                    num_str = '0' + vat[1:8]
                elif vat[0] == 'Y':
                    num_str = '1' + vat[1:8]
                elif vat[0] == 'Z':
                    num_str = '2' + vat[1:8]
                else:
                    num_str = vat[:8]
                
                expected_letter = mapping[int(num_str) % 23]
                if vat[8] != expected_letter:
                    raise ValidationError(_("Invalid DNI/NIE: The control letter '%s' does not match for number %s. Expected '%s'.") % (vat[8], vat[:8], expected_letter))

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