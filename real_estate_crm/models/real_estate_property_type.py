from odoo import api, fields, models, _


class RealEstatePropertyType(models.Model):
    _name = 'real.estate.property.type'
    _description = 'Real Estate Property Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    
    property_count = fields.Integer(
        string='Properties',
        compute='_compute_property_count'
    )
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Property type code must be unique!')
    ]
    
    def _compute_property_count(self):
        for record in self:
            record.property_count = self.env['real.estate.property'].search_count([
                ('property_type_id', '=', record.id)
            ])
    
    def action_view_properties(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_property')
        action['domain'] = [('property_type_id', '=', self.id)]
        action['context'] = {'default_property_type_id': self.id}
        return action
