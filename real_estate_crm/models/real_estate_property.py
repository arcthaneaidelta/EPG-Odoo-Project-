from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # Basic Information
    name = fields.Char(
        string='Property Name',
        required=True,
        tracking=True,
        index=True
    )
    
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    # Property Classification
    property_type_id = fields.Many2one(
        'real.estate.property.type',
        string='Property Type',
        required=True,
        tracking=True
    )
    
    transaction_type = fields.Selection([
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('both', 'Sale & Rent'),
    ], string='Transaction Type', required=True, default='sale', tracking=True)
    
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
        ('unavailable', 'Unavailable'),
    ], string='Status', default='available', required=True, tracking=True)
    
    # Location
    address = fields.Char(string='Address', tracking=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP Code')
    country_id = fields.Many2one('res.country', string='Country')
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    
    # Financial Information
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    price = fields.Monetary(
        string='Sale Price',
        currency_field='currency_id',
        tracking=True
    )
    
    rental_price = fields.Monetary(
        string='Rental Price',
        currency_field='currency_id',
        tracking=True
    )
    
    rental_period = fields.Selection([
        ('monthly', 'Per Month'),
        ('yearly', 'Per Year'),
    ], string='Rental Period', default='monthly')
    
    # Property Details
    bedrooms = fields.Integer(string='Bedrooms', default=0)
    bathrooms = fields.Integer(string='Bathrooms', default=0)
    living_area = fields.Float(string='Living Area (m²)')
    total_area = fields.Float(string='Total Area (m²)')
    floor = fields.Integer(string='Floor')
    total_floors = fields.Integer(string='Total Floors')
    year_built = fields.Integer(string='Year Built')
    
    # Features
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Garden')
    swimming_pool = fields.Boolean(string='Swimming Pool')
    elevator = fields.Boolean(string='Elevator')
    balcony = fields.Boolean(string='Balcony')
    furnished = fields.Boolean(string='Furnished')
    
    description = fields.Html(string='Description')
    
    # Relationships
    agent_id = fields.Many2one(
        'res.users',
        string='Agent',
        tracking=True,
        default=lambda self: self.env.user,
        index=True
    )
    
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        tracking=True,
        domain="[('company_id', 'in', [company_id, False])]"
    )
    
    # CRM Integration
    lead_ids = fields.One2many(
        'crm.lead',
        'property_id',
        string='Opportunities'
    )
    
    lead_count = fields.Integer(
        string='Opportunities',
        compute='_compute_lead_count'
    )
    
    # Rental Management
    rental_contract_ids = fields.One2many(
        'real.estate.rental.contract',
        'property_id',
        string='Rental Contracts'
    )
    
    active_rental_contract_id = fields.Many2one(
        'real.estate.rental.contract',
        string='Active Contract',
        compute='_compute_active_rental_contract',
        store=True
    )
    
    rental_contract_count = fields.Integer(
        string='Contracts',
        compute='_compute_rental_contract_count'
    )
    
    # Visits
    visit_ids = fields.One2many(
        'real.estate.visit',
        'property_id',
        string='Visits'
    )
    
    visit_count = fields.Integer(
        string='Visits',
        compute='_compute_visit_count'
    )
    
    # Commissions
    commission_ids = fields.One2many(
        'real.estate.commission',
        'property_id',
        string='Commissions'
    )
    
    commission_count = fields.Integer(
        string='Commissions',
        compute='_compute_commission_count'
    )
    
    # MLS Integration Preparation
    mls_external_id = fields.Char(
        string='MLS External ID',
        help='External ID for MLS portal synchronization'
    )
    
    mls_status = fields.Selection([
        ('pending', 'Pending Export'),
        ('exported', 'Exported'),
        ('error', 'Export Error'),
    ], string='MLS Status', default='pending')
    
    mls_last_sync = fields.Datetime(string='Last MLS Sync')
    mls_error_message = fields.Text(string='MLS Error Message')
    
    # Images
    image_1920 = fields.Image(string='Main Image', max_width=1920, max_height=1920)
    image_1024 = fields.Image(string='Image 1024', related='image_1920', max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image(string='Image 512', related='image_1920', max_width=512, max_height=512, store=True)
    image_256 = fields.Image(string='Image 256', related='image_1920', max_width=256, max_height=256, store=True)
    image_128 = fields.Image(string='Image 128', related='image_1920', max_width=128, max_height=128, store=True)
    
    # Computed Fields
    full_address = fields.Char(
        string='Full Address',
        compute='_compute_full_address',
        store=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('real.estate.property') or _('New')
        return super(RealEstateProperty, self).create(vals)
    
    @api.depends('street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _compute_full_address(self):
        for record in self:
            address_parts = []
            if record.street:
                address_parts.append(record.street)
            if record.street2:
                address_parts.append(record.street2)
            if record.city:
                address_parts.append(record.city)
            if record.state_id:
                address_parts.append(record.state_id.name)
            if record.zip:
                address_parts.append(record.zip)
            if record.country_id:
                address_parts.append(record.country_id.name)
            record.full_address = ', '.join(address_parts)
    
    def _compute_lead_count(self):
        for record in self:
            record.lead_count = len(record.lead_ids)

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        """
        Automatically convert ALL financial values in this property 
        and its children (contracts/commissions) when currency changes.
        """
        # 1. Check if we have a previous currency to convert FROM
        if self.currency_id and self._origin.currency_id and self.currency_id != self._origin.currency_id:
            
            from_curr = self._origin.currency_id
            to_curr = self.currency_id
            company = self.company_id or self.env.company
            date = fields.Date.today()

            # --- A. CONVERT PROPERTY VALUES ---
            if self.price:
                self.price = from_curr._convert(self.price, to_curr, company, date)
            if self.rental_price:
                self.rental_price = from_curr._convert(self.rental_price, to_curr, company, date)

            # --- B. CONVERT LINKED RENTAL CONTRACTS ---
            for contract in self.rental_contract_ids:
                # 1. Convert Rent
                if contract.recurring_amount:
                    contract.recurring_amount = from_curr._convert(
                        contract.recurring_amount, to_curr, company, date
                    )
                # 2. Convert Deposit (ADDED AS REQUESTED)
                if contract.deposit_amount:
                    contract.deposit_amount = from_curr._convert(
                        contract.deposit_amount, to_curr, company, date
                    )

            # --- C. CONVERT LINKED COMMISSIONS ---
            for commission in self.commission_ids:
                # 1. Convert Final Amount
                if commission.amount:
                    commission.amount = from_curr._convert(
                        commission.amount, to_curr, company, date
                    )
                # 2. Convert Base Amount (ADDED AS REQUESTED)
                if commission.base_amount:
                    commission.base_amount = from_curr._convert(
                        commission.base_amount, to_curr, company, date
                    )
    
    @api.depends('rental_contract_ids', 'rental_contract_ids.state')
    def _compute_active_rental_contract(self):
        for record in self:
            active_contract = record.rental_contract_ids.filtered(
                lambda c: c.state == 'active'
            )
            record.active_rental_contract_id = active_contract[:1] if active_contract else False
    
    def _compute_rental_contract_count(self):
        for record in self:
            record.rental_contract_count = len(record.rental_contract_ids)
    
    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)
    
    def _compute_commission_count(self):
        for record in self:
            record.commission_count = len(record.commission_ids)
    
    @api.constrains('price', 'rental_price')
    def _check_prices(self):
        for record in self:
            if record.transaction_type in ['sale', 'both'] and record.price <= 0:
                raise ValidationError(_('Sale price must be greater than zero for properties for sale.'))
            if record.transaction_type in ['rent', 'both'] and record.rental_price <= 0:
                raise ValidationError(_('Rental price must be greater than zero for properties for rent.'))
    
    def action_view_leads(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {
            'default_property_id': self.id,
            'default_type': 'opportunity',
        }
        return action
    
    def action_view_rental_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_rental_contract')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action
    
    def action_view_visits(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_visit')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action
    
    def action_view_commissions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_commission')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action
    
    def action_create_opportunity(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Opportunity'),
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.id,
                'default_type': 'opportunity',
                'default_name': f'Opportunity - {self.name}',
            },
            'target': 'current',
        }
    
    def action_schedule_visit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Visit'),
            'res_model': 'real.estate.visit',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.id,
            },
            'target': 'new',
        }
    
    def action_set_available(self):
        for record in self:
            record.state = 'available'
    
    def action_set_reserved(self):
        for record in self:
            record.state = 'reserved'
    
    def action_set_sold(self):
        for record in self:
            record.state = 'sold'
    
    def action_set_rented(self):
        for record in self:
            record.state = 'rented'
    
    def action_export_to_mls(self):
        """Placeholder for MLS export functionality"""
        for record in self:
            # This will be implemented in Phase 2
            record.message_post(
                body=_('MLS Export feature will be implemented in Phase 2'),
                subject=_('MLS Export')
            )
            record.mls_status = 'pending'
