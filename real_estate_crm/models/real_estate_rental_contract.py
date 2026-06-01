from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class RealEstateRentalContract(models.Model):
    _name = 'real.estate.rental.contract'
    _description = 'Real Estate Rental Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(
        string='Contract Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    active = fields.Boolean(string='Active', default=True)
    
    # Parties
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='property_id.currency_id',
        string='Currency',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        required=True,
        tracking=True,
        domain="[('company_id', 'in', [company_id, False])]"
    )
    
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        required=True,
        tracking=True,
        domain="[('transaction_type', 'in', ['rent', 'both']), ('company_id', '=', company_id)]"
    )
    
    agent_id = fields.Many2one(
        'res.users',
        string='Agent',
        tracking=True,
        default=lambda self: self.env.user
    )
    
    # Financial Terms
    recurring_amount = fields.Monetary(
        string='Rental Amount',
        currency_field='currency_id',
        required=True,
        tracking=True
    )
    
    recurring_unit = fields.Selection([
        ('month', 'Monthly'),
        ('year', 'Yearly'),
    ], string='Billing Period', required=True, default='month', tracking=True)
    
    deposit_amount = fields.Monetary(
        string='Security Deposit',
        currency_field='currency_id',
        tracking=True
    )
    
    deposit_paid = fields.Boolean(string='Deposit Paid', tracking=True)
    deposit_date = fields.Date(string='Deposit Payment Date')
    
    # Contract Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        tracking=True
    )
    
    next_invoice_date = fields.Date(
        string='Next Invoice Date',
        tracking=True
    )
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Invoicing
    invoice_ids = fields.One2many(
        'account.move',
        'rental_contract_id',
        string='Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    invoice_count = fields.Integer(
        string='Invoices',
        compute='_compute_invoice_count'
    )
    
    # Additional Information
    notes = fields.Text(string='Notes')
    terms = fields.Html(string='Terms and Conditions')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.rental.contract') or _('New')
        
        # Set initial next_invoice_date if not provided
        if not vals.get('next_invoice_date') and vals.get('start_date'):
            vals['next_invoice_date'] = vals['start_date']
        
        return super(RealEstateRentalContract, self).create(vals)
    
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('property_id', 'start_date', 'end_date', 'state')
    def _check_property_availability(self):
        """Ensure property is not double-booked"""
        for record in self:
            if record.state == 'active':
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('property_id', '=', record.property_id.id),
                    ('state', '=', 'active'),
                    '|',
                    '&', ('start_date', '<=', record.start_date), 
                         '|', ('end_date', '>=', record.start_date), ('end_date', '=', False),
                    '&', ('start_date', '<=', record.end_date if record.end_date else fields.Date.today()), 
                         '|', ('end_date', '>=', record.start_date), ('end_date', '=', False),
                ])
                if overlapping:
                    raise ValidationError(_(
                        'This property already has an active rental contract for the specified period.'
                    ))
    
    def action_confirm(self):
        """Activate the rental contract"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft contracts can be confirmed.'))
            
            # Update property state
            if record.property_id:
                record.property_id.write({'state': 'rented'})
            
            # Set next invoice date if not set
            if not record.next_invoice_date:
                record.next_invoice_date = record.start_date
            
            record.write({'state': 'active'})
            
            # Create commission for the agent
            self.env['real.estate.commission'].create({
                'contract_id': record.id,
                'property_id': record.property_id.id,
                'agent_id': record.agent_id.id,
                'commission_type': 'rent',
                'base_amount': record.recurring_amount,
            })
            
            record.message_post(
                body=_('Rental contract confirmed and activated.'),
                subject=_('Contract Activated')
            )
    
    def action_close(self):
        """Close the rental contract"""
        for record in self:
            if record.state != 'active':
                raise UserError(_('Only active contracts can be closed.'))
            
            # Update property state if no other active contracts
            if record.property_id:
                other_active = self.search([
                    ('id', '!=', record.id),
                    ('property_id', '=', record.property_id.id),
                    ('state', '=', 'active')
                ])
                if not other_active:
                    record.property_id.write({'state': 'available'})
            
            record.write({'state': 'closed'})
            record.message_post(
                body=_('Rental contract closed.'),
                subject=_('Contract Closed')
            )
    
    def action_cancel(self):
        """Cancel the rental contract"""
        for record in self:
            if record.state == 'closed':
                raise UserError(_('Closed contracts cannot be cancelled.'))
            
            # Update property state if currently active
            if record.state == 'active' and record.property_id:
                other_active = self.search([
                    ('id', '!=', record.id),
                    ('property_id', '=', record.property_id.id),
                    ('state', '=', 'active')
                ])
                if not other_active:
                    record.property_id.write({'state': 'available'})
            
            record.write({'state': 'cancelled'})
            record.message_post(
                body=_('Rental contract cancelled.'),
                subject=_('Contract Cancelled')
            )
    
    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('rental_contract_id', '=', self.id)]
        action['context'] = {
            'default_move_type': 'out_invoice',
            'default_rental_contract_id': self.id,
            'default_partner_id': self.partner_id.id,
        }
        return action
    
    def _create_invoice(self):
        """Create recurring invoice for this contract"""
        self.ensure_one()
        
        if self.state != 'active':
            return False
        
        if not self.next_invoice_date or self.next_invoice_date > fields.Date.today():
            return False
        
        # Check if invoice already exists for this period
        existing_invoice = self.env['account.move'].search([
            ('rental_contract_id', '=', self.id),
            ('invoice_date', '=', self.next_invoice_date),
            ('state', '!=', 'cancel'),
        ], limit=1)
        
        if existing_invoice:
            return False  # Avoid duplicates
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.next_invoice_date,
            'rental_contract_id': self.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': _('Rent - %s - %s') % (
                    self.property_id.name,
                    self.next_invoice_date.strftime('%B %Y')
                ),
                'quantity': 1,
                'price_unit': self.recurring_amount,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Update next invoice date
        if self.recurring_unit == 'month':
            next_date = self.next_invoice_date + relativedelta(months=1)
        else:  # yearly
            next_date = self.next_invoice_date + relativedelta(years=1)
        
        # Don't create invoices beyond contract end date
        if self.end_date and next_date > self.end_date:
            next_date = False
        
        self.write({'next_invoice_date': next_date})
        
        self.message_post(
            body=_('Recurring invoice created: %s') % invoice.name,
            subject=_('Invoice Created')
        )
        
        return invoice
    
    @api.model
    def cron_create_recurring_invoices(self):
        """Cron job to create recurring invoices for all active contracts"""
        contracts = self.search([
            ('state', '=', 'active'),
            ('next_invoice_date', '<=', fields.Date.today()),
        ])
        
        created_invoices = self.env['account.move']
        for contract in contracts:
            invoice = contract._create_invoice()
            if invoice:
                created_invoices |= invoice
        
        return created_invoices
