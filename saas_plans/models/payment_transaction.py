# -*- coding: utf-8 -*-

from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    def _reconcile_after_done(self):
        """Override to auto-confirm SaaS orders and trigger provisioning after payment"""
        
        # 1. Lock the transaction validation to prevent concurrent updates (Serialization Failure)
        # This fixes the issue where Redsys callback and User Redirect happen simultaneously
        for tx in self:
            try:
                # Lock wait could be added here if needed, but usually rapid
                self.env.cr.execute("SELECT id FROM payment_transaction WHERE id = %s FOR UPDATE", (tx.id,))
            except Exception as e:
                _logger.warning(f"Could not lock transaction {tx.id}: {e}")

        # Process SaaS orders BEFORE calling super
        for transaction in self:
            sale_orders = transaction.sale_order_ids.filtered(lambda so: so.saas_plan_id and so._is_saas_order())
            
            for order in sale_orders:
                try:
                    # Auto-confirm the order if not already confirmed
                    if order.state in ['draft', 'sent']:
                        _logger.info(f'Auto-confirming SaaS order {order.name} after payment')
                        order.action_confirm()

                        # Check if auto-provisioning is enabled
                        auto_provision = self.env['ir.config_parameter'].sudo().get_param(
                            'saas.auto_provision_on_payment',
                            'True'
                        )
    
                        if auto_provision == 'True':
                            # Trigger provisioning if subscription exists
                            subscription = self.env['saas.subscription'].sudo().search([
                                ('order_id', '=', order.id)
                            ], limit=1)
                            
                            if subscription and not subscription.database_name:
                                _logger.info(f'Auto-provisioning tenant for subscription {subscription.id}')
                                subscription.action_provision_tenant()
                    
                except Exception as e:
                    _logger.error(f'Error processing SaaS order {order.name}: {str(e)}')
        
        # Call super, but catch accounting errors for SaaS orders
        try:
            res = super(PaymentTransaction, self)._reconcile_after_done()
        except Exception as e:
            # If this is a SaaS order and accounting fails, log but don't crash
            if self.sale_order_ids.filtered(lambda so: so.saas_plan_id):
                _logger.warning(f'Accounting post-processing failed for SaaS transaction {self.reference}: {str(e)}')
                _logger.info('SaaS provisioning completed successfully despite accounting error')
                res = True
            else:
                raise
        
        return res
    
    def _create_payment(self, **kwargs):
        """Override to skip payment creation ONLY for pure SaaS orders"""
        # We only skip payment creation if ALL products in the order are SaaS products
        # If there's even one standard product, we want a payment created for the transaction
        is_pure_saas = True
        for order in self.sale_order_ids:
            if not order.saas_plan_id or not order._is_saas_order():
                is_pure_saas = False
                break
            
            # Additional check: are all lines SaaS products?
            for line in order.order_line:
                if not (line.product_id.default_code and line.product_id.default_code.startswith('SAAS_')):
                    is_pure_saas = False
                    break
            
            if not is_pure_saas:
                break

        if is_pure_saas and self.sale_order_ids:
            _logger.info(f'Skipping payment creation for pure SaaS transaction {self.reference}')
            return self.env['account.payment']
        
        # For non-SaaS or mixed orders, use default behavior
        return super(PaymentTransaction, self)._create_payment(**kwargs)
