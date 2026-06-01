from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RealEstateCommission(models.Model):
    _name = 'real.estate.commission'
    _description = 'Real Estate Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Commission Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    # Related Records
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
    
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    agent_id = fields.Many2one(
        'res.users',
        string='Agent',
        required=True,
        tracking=True,
        default=lambda self: self.env.user
    )
    
    lead_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        tracking=True,
        domain="[('type', '=', 'opportunity'), ('company_id', '=', company_id)]"
    )
    
    contract_id = fields.Many2one(
        'real.estate.rental.contract',
        string='Rental Contract',
        tracking=True
    )
    
    # Commission Details
    commission_type = fields.Selection([
        ('sale', 'Sale Commission'),
        ('rent', 'Rental Commission'),
    ], string='Commission Type', required=True, tracking=True)
    
    base_amount = fields.Monetary(
        string='Base Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='The amount on which commission is calculated (sale price or rental amount)'
    )
    
    rate = fields.Float(
        string='Commission Rate (%)',
        default=3.0,
        tracking=True,
        help='Commission percentage'
    )
    
    amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_amount',
        store=True,
        tracking=True
    )
    
    fixed_amount = fields.Monetary(
        string='Fixed Commission Amount',
        currency_field='currency_id',
        help='If set, this fixed amount will be used instead of percentage calculation'
    )
    
    calculation_method = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Calculation Method', default='percentage', required=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Payment
    payment_date = fields.Date(string='Payment Date')
    
    # Additional Info
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.commission') or _('New')
        
        # Auto-confirm if created from contract or closed won opportunity
        commission = super(RealEstateCommission, self).create(vals)
        
        if commission.contract_id and commission.contract_id.state == 'active':
            commission.action_confirm()
        
        return commission
    
    @api.depends('base_amount', 'rate', 'fixed_amount', 'calculation_method')
    def _compute_amount(self):
        for record in self:
            if record.calculation_method == 'fixed':
                record.amount = record.fixed_amount
            else:
                record.amount = record.base_amount * (record.rate / 100.0)
    
    @api.constrains('rate')
    def _check_rate(self):
        for record in self:
            if record.calculation_method == 'percentage' and (record.rate < 0 or record.rate > 100):
                raise ValidationError(_('Commission rate must be between 0 and 100.'))
    
    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                continue
            
            record.state = 'confirmed'
            record.message_post(
                body=_('Commission confirmed: %s %s') % (
                    record.amount,
                    record.currency_id.symbol
                ),
                subject=_('Commission Confirmed')
            )
    
    def action_mark_paid(self):
        for record in self:
            if record.state != 'confirmed':
                continue
            
            record.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
            })
            record.message_post(
                body=_('Commission marked as paid.'),
                subject=_('Commission Paid')
            )
    
    def action_cancel(self):
        for record in self:
            if record.state == 'paid':
                raise ValidationError(_('Cannot cancel a paid commission.'))
            
            record.state = 'cancelled'
            record.message_post(
                body=_('Commission cancelled.'),
                subject=_('Commission Cancelled')
            )
    
    def action_reset_to_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise ValidationError(_('Only cancelled commissions can be reset to draft.'))
            
            record.state = 'draft'
