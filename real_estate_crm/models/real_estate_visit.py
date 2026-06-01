from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RealEstateVisit(models.Model):
    _name = 'real.estate.visit'
    _description = 'Real Estate Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_datetime desc, id desc'

    name = fields.Char(
        string='Visit Reference',
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
    
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    lead_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        tracking=True,
        domain="[('type', '=', 'opportunity'), ('company_id', '=', company_id), ('property_id','!=',False), ('property_id','=',property_id)] "
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Visitor',
        required=True,
        tracking=True,
        domain="[('company_id', 'in', [company_id, False])]"
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Agent',
        required=True,
        tracking=True,
        default=lambda self: self.env.user
    )
    
    # Visit Details
    visit_datetime = fields.Datetime(
        string='Visit Date & Time',
        required=True,
        tracking=True,
        default=fields.Datetime.now
    )
    
    duration = fields.Float(
        string='Duration (hours)',
        default=1.0
    )
    
    state = fields.Selection([
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='planned', required=True, tracking=True)
    
    # Feedback
    visitor_feedback = fields.Selection([
        ('very_interested', 'Very Interested'),
        ('interested', 'Interested'),
        ('neutral', 'Neutral'),
        ('not_interested', 'Not Interested'),
    ], string='Visitor Feedback', tracking=True)
    
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    
    # Calendar Integration
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        readonly=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.visit') or _('New')
        
        visit = super(RealEstateVisit, self).create(vals)
        
        # Create calendar event
        if visit.visit_datetime and visit.user_id:
            visit._create_calendar_event()
        
        return visit
    
    def write(self, vals):
        result = super(RealEstateVisit, self).write(vals)
        
        # Update calendar event if datetime or user changed
        if 'visit_datetime' in vals or 'user_id' in vals:
            for visit in self:
                if visit.calendar_event_id:
                    visit._update_calendar_event()
        
        return result
    
    def unlink(self):
        # Delete associated calendar events
        calendar_events = self.mapped('calendar_event_id')
        result = super(RealEstateVisit, self).unlink()
        calendar_events.unlink()
        return result
    
    def _create_calendar_event(self):
        """Create a calendar event for this visit"""
        self.ensure_one()
        
        if self.calendar_event_id:
            return
        
        event_vals = {
            'name': _('Visit: %s') % self.property_id.name,
            'start': self.visit_datetime,
            'stop': fields.Datetime.add(self.visit_datetime, hours=self.duration),
            'user_id': self.user_id.id,
            'partner_ids': [(4, self.partner_id.id)],
            'description': _('Property Visit\n\nProperty: %s\nVisitor: %s\nAgent: %s\n\nNotes:\n%s') % (
                self.property_id.name,
                self.partner_id.name,
                self.user_id.name,
                self.notes or ''
            ),
        }
        
        event = self.env['calendar.event'].create(event_vals)
        self.calendar_event_id = event.id
    
    def _update_calendar_event(self):
        """Update the associated calendar event"""
        self.ensure_one()
        
        if not self.calendar_event_id:
            self._create_calendar_event()
            return
        
        self.calendar_event_id.write({
            'start': self.visit_datetime,
            'stop': fields.Datetime.add(self.visit_datetime, hours=self.duration),
            'user_id': self.user_id.id,
        })
    
    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'
            record.message_post(
                body=_('Visit confirmed.'),
                subject=_('Visit Confirmed')
            )
    
    def action_done(self):
        for record in self:
            record.state = 'done'
            record.message_post(
                body=_('Visit completed.'),
                subject=_('Visit Completed')
            )
            
            # Update opportunity if linked
            if record.lead_id:
                record.lead_id.message_post(
                    body=_('Visit completed for property: %s') % record.property_id.name,
                    subject=_('Visit Completed')
                )
    
    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'
            record.message_post(
                body=_('Visit cancelled.'),
                subject=_('Visit Cancelled')
            )
    
    def action_no_show(self):
        for record in self:
            record.state = 'no_show'
            record.message_post(
                body=_('Visitor did not show up.'),
                subject=_('No Show')
            )
    
    @api.constrains('visit_datetime')
    def _check_visit_datetime(self):
        for record in self:
            if record.visit_datetime and record.visit_datetime < fields.Datetime.now():
                if record.state == 'planned':
                    raise ValidationError(_('Visit date/time cannot be in the past for planned visits.'))
