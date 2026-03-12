from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_outbound_payment_method_line_id = fields.Many2one(
        help="Preferred payment method when buying from this vendor. This will be set by default on all"
             " outgoing payments created for this vendor.\n"
             "Manual option represents payments handled outside the system natively, like cash or external bank transfers."
    )

    property_inbound_payment_method_line_id = fields.Many2one(
        help="Preferred payment method when selling to this customer. This will be set by default on all"
             " incoming payments created for this customer.\n"
             "Manual option represents payments handled outside the system natively, like cash or external bank transfers."
    )
