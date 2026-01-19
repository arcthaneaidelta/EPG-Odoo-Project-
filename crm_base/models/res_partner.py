from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        # Create the partner(s) first
        partners = super(ResPartner, self).create(vals_list)
        
        # Get the email template
        template = self.env.ref('crm_base.email_template_welcome_new_customer', raise_if_not_found=False)
        
        # Send email to each new customer
        for partner in partners:
            # Only send if it's a customer and has an email
            if partner.customer_rank > 0 and partner.email and template:
                template.send_mail(partner.id, force_send=True)
        
        return partners