from odoo import api, fields, models, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Property linking
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    # Visits
    visit_ids = fields.One2many(
        'real.estate.visit',
        'lead_id',
        string='Visits'
    )
    
    visit_count = fields.Integer(
        string='Visits',
        compute='_compute_visit_count'
    )
    
    # Commissions
    commission_ids = fields.One2many(
        'real.estate.commission',
        'lead_id',
        string='Commissions'
    )
    
    commission_count = fields.Integer(
        string='Commissions',
        compute='_compute_commission_count'
    )
    
    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)
    
    def _compute_commission_count(self):
        for record in self:
            record.commission_count = len(record.commission_ids)
    
    def action_schedule_visit(self):
        self.ensure_one()
        
        if not self.property_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Property'),
                    'message': _('Please select a property first.'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Visit'),
            'res_model': 'real.estate.visit',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.property_id.id,
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'new',
        }
    
    def action_view_visits(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_visit')
        action['domain'] = [('lead_id', '=', self.id)]
        action['context'] = {
            'default_lead_id': self.id,
            'default_property_id': self.property_id.id if self.property_id else False,
            'default_partner_id': self.partner_id.id,
        }
        return action
    
    def action_view_commissions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('real_estate_crm.action_real_estate_commission')
        action['domain'] = [('lead_id', '=', self.id)]
        action['context'] = {
            'default_lead_id': self.id,
            'default_property_id': self.property_id.id if self.property_id else False,
        }
        return action
    
    def action_set_won(self):
        """Override to create commission when opportunity is won"""
        res = super(CrmLead, self).action_set_won()
        
        for lead in self:
            if lead.property_id and lead.property_id.transaction_type in ['sale', 'both']:
                # Create sale commission
                self.env['real.estate.commission'].create({
                    'lead_id': lead.id,
                    'property_id': lead.property_id.id,
                    'agent_id': lead.user_id.id,
                    'commission_type': 'sale',
                    'base_amount': lead.property_id.price or lead.expected_revenue,
                })
                
                # Update property state
                lead.property_id.write({'state': 'sold'})
        
        return res

    #------------- In case of any error --------------
    # def action_set_won(self):
    #     # Execute standard logic
    #     res = super(CrmLead, self).action_set_won()
        
    #     # NEW: Flush the pending background changes to DB 
    #     # before we start our custom logic to avoid serialization errors
    #     self.flush_recordset()

    #     for lead in self:
    #         # Check for real ID and avoid NewId
    #         if not isinstance(lead.id, models.NewId) and lead.property_id:
    #             # Check if property is also real
    #             if not isinstance(lead.property_id.id, models.NewId):
    #                 self._create_lead_commission(lead)
    #     return res

    # def _create_lead_commission(self, lead):
    #     """Helper to isolate logic and keep it clean"""
    #     if lead.property_id.transaction_type in ['sale', 'both']:
    #         # Create commission
    #         self.env['real.estate.commission'].sudo().create({
    #             'lead_id': lead.id,
    #             'property_id': lead.property_id.id,
    #             'agent_id': lead.user_id.id,
    #             'commission_type': 'sale',
    #             'base_amount': lead.property_id.price or lead.expected_revenue,
    #         })
    #         # Update property
    #         lead.property_id.write({'state': 'sold'})