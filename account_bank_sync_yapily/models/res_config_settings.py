from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    yapily_application_uuid = fields.Char(related='company_id.yapily_application_uuid', readonly=False)
    yapily_secret = fields.Char(related='company_id.yapily_secret', readonly=False)
    yapily_api_url = fields.Char(related='company_id.yapily_api_url', readonly=False)
