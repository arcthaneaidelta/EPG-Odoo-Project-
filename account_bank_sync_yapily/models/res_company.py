from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    yapily_application_uuid = fields.Char(string='Yapily Application UUID')
    yapily_secret = fields.Char(string='Yapily Secret')
    yapily_api_url = fields.Char(string='Yapily API URL', default="https://api.yapily.com")
