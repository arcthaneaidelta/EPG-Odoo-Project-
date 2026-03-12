# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaaSSubscription(models.Model):
    _inherit = 'saas.subscription'
    
    provisioning_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Provisioning Status', default='not_started', readonly=True)
    
    provisioning_error = fields.Text(string='Provisioning Error', readonly=True)
    admin_password = fields.Char(string='Admin Password', readonly=True, copy=False,
                                  help='Initial admin password for the tenant database')
    
    def write(self, vals):
        # Call super first
        res = super(SaaSSubscription, self).write(vals)
        
        # Check if we need to push limits to tenant
        # Trigger if plan, extra_users, extra_storage changed, or if state became active
        if any(f in vals for f in ['plan_id', 'extra_users', 'extra_storage_gb', 'state']):
            for sub in self:
                if sub.state == 'active' and sub.database_name:
                    sub._push_limits_to_tenant()
        
        # Status Push
        if 'state' in vals:
            for sub in self:
                if sub.database_name:
                     # Map state to simple status
                     status = 'suspended' if sub.state == 'suspended' else 'active'
                     sub._push_status_to_tenant(status)
        
        return res

    def _push_status_to_tenant(self, status):
        """Push subscription status to tenant (active/suspended)"""
        for sub in self:
            if not sub.database_name:
                continue
            
            try:
                _logger.info(f"Pushing status {status} to tenant {sub.database_name}")
                
                import odoo
                registry = odoo.registry(sub.database_name)
                
                with registry.cursor() as cr:
                    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                    env['ir.config_parameter'].set_param('saas.subscription_status', status)
                    
            except Exception as e:
                _logger.error(f"Failed to push status to tenant {sub.database_name}: {str(e)}")

    def _push_limits_to_tenant(self):
        """Push usage limits to the tenant database parameters"""
        for sub in self:
            if not sub.database_name:
                continue
                
            try:
                # Calculate limits
                # Handle case where total_users might not be computed yet if called during write? 
                # explicit recompute or trust stored value. Stored value should be updated by super.write
                
                max_users = sub.total_users
                max_storage_mb = int(sub.total_storage_gb * 1024) # GB to MB
                
                _logger.info(f"Pushing limits to {sub.database_name}: Users={max_users}, Storage={max_storage_mb}MB")
                
                import odoo
                registry = odoo.registry(sub.database_name)
                
                with registry.cursor() as cr:
                    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                    
                    # atomic update of parameters
                    env['ir.config_parameter'].set_param('saas.max_users', str(max_users))
                    env['ir.config_parameter'].set_param('saas.max_storage_mb', str(max_storage_mb))
                    
                    # Push connection info for portal management
                    if sub.access_token:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        env['ir.config_parameter'].set_param('saas.manager_url', base_url)
                        env['ir.config_parameter'].set_param('saas.subscription_token', sub.access_token)
                        
                    # Also push initial status if not set? 
                    # Usually active on creation, but let's ensure compliance
                    current_status = 'suspended' if sub.state == 'suspended' else 'active'
                    env['ir.config_parameter'].set_param('saas.subscription_status', current_status)
                    
            except Exception as e:
                _logger.error(f"Failed to push limits to tenant {sub.database_name}: {str(e)}")

    def action_provision_tenant(self):
        """Manually trigger tenant provisioning"""
        self.ensure_one()
        
        if self.database_name:
            raise UserError(_('Tenant already provisioned. Database: %s') % self.database_name)
        
        if not self.company_name:
            raise UserError(_('Company name is required for provisioning'))
        
        # Call provisioning service
        provisioning_service = self.env['saas.provisioning.service']
        try:
            result = provisioning_service.provision_tenant(self.id)
            if result:
                # Push initial limits
                self._push_limits_to_tenant()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Tenant provisioned successfully!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Provisioning failed: %s') % str(e))
    
    def _schedule_tenant_deletion(self):
        """Override from saas_management to actually delete tenant"""
        _logger.info(f'Scheduling tenant deletion for {self.name}')
        
        # Call deletion service
        provisioning_service = self.env['saas.provisioning.service']
        try:
            provisioning_service.delete_tenant(
                subscription_id=self.id,
                backup=True
            )
        except Exception as e:
            _logger.error(f'Tenant deletion failed for {self.name}: {str(e)}')
            self.write({
                'state': 'error',
                'error_message': f'Deletion failed: {str(e)}'
            })
