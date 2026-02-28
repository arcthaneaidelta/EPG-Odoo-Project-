from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    referrer_user_id = fields.Many2one('res.users', string="Referrer")
    referral_code = fields.Char(string="Referral Code")
    saas_payment_email_sent = fields.Boolean("SaaS Payment Email Sent", default=False, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # When creating an invoice naturally, if we have a partner, grab their referral data
            if vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if partner.exists():
                    if partner.referral_code and not vals.get('referral_code'):
                        vals['referral_code'] = partner.referral_code
                    if partner.referrer_user_id and not vals.get('referrer_user_id'):
                        vals['referrer_user_id'] = partner.referrer_user_id.id
                        
        return super(AccountMove, self).create(vals_list)

    @api.onchange('partner_id')
    def _onchange_partner_id_referral(self):
        """Update referral code on invoice UI when partner changes"""
        for move in self:
            if move.partner_id:
                if move.partner_id.referral_code and not move.referral_code:
                    move.referral_code = move.partner_id.referral_code
                if move.partner_id.referrer_user_id and not move.referrer_user_id:
                    move.referrer_user_id = move.partner_id.referrer_user_id
