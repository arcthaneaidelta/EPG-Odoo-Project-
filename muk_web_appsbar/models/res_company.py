from odoo import models, fields, api, tools
import base64


class ResCompany(models.Model):
    
    _inherit = 'res.company'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    appbar_image = fields.Binary(
        string='Apps Menu Footer Image',
        attachment=True
    )
