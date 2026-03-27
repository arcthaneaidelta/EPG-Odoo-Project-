from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    url_replace_enabled = fields.Boolean(
        string="Activate URL Substitution",
        config_parameter='web.url.replace.enabled',
        help="Activate to replace '/odoo' in URLs."
    )
    url_replace_text = fields.Char(
        string="Brand Name",
        config_parameter='web.base.sorturl',
        default="odoo",
        help="The name to replace '/odoo' with in URLs."
    )
