from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Property ownership
    owned_property_ids = fields.One2many(
        'real.estate.property',
        'owner_id',
        string='Owned Properties'
    )
    
    owned_property_count = fields.Integer(
        string='Properties Owned',
        compute='_compute_owned_property_count'
    )
    
    # Rental contracts
    rental_contract_ids = fields.One2many(
        'real.estate.rental.contract',
        'partner_id',
        string='Rental Contracts'
    )
    
    rental_contract_count = fields.Integer(
        string='Rental Contracts',
        compute='_compute_rental_contract_count'
    )
    
    # Visits
    visit_ids = fields.One2many(
        'real.estate.visit',
        'partner_id',
        string='Property Visits'
    )
    
    visit_count = fields.Integer(
        string='Visits',
        compute='_compute_visit_count'
    )
    
    # Partner Type
    is_property_owner = fields.Boolean(string='Is Property Owner')
    is_tenant = fields.Boolean(string='Is Tenant')
    
    def _compute_owned_property_count(self):
        for record in self:
            record.owned_property_count = len(record.owned_property_ids)
    
    def _compute_rental_contract_count(self):
        for record in self:
            record.rental_contract_count = len(record.rental_contract_ids)
    
    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)
    
    def action_view_owned_properties(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_property')
        action['domain'] = [('owner_id', '=', self.id)]
        action['context'] = {'default_owner_id': self.id}
        return action
    
    def action_view_rental_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_rental_contract')
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
    
    def action_view_visits(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_visit')
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
