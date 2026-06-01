# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    saas_onboarding_done = fields.Boolean(
        string="SaaS Onboarding Done",
        default=False,
        help="Technical field to track if the client has completed the initial setup wizard."
    )
