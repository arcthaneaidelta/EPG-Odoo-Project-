# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
	_inherit = 'sale.order'
	
	# SaaS-specific fields
	saas_company_name = fields.Char(string='Company Name (for SaaS)')
	saas_plan_id = fields.Many2one('saas.plan', string='SaaS Plan')
	saas_billing_cycle = fields.Selection([
		('monthly', 'Monthly'),
		('annual', 'Annual'),
	], string='Billing Cycle')
	saas_subscription_id = fields.Many2one('saas.subscription', string='Created Subscription', readonly=True)
	saas_subscription_origin_id = fields.Many2one('saas.subscription', string='Subscription to Renew/Upgrade', readonly=True, help='Reference to the subscription being renewed or upgraded')
	
	# Promo code fields
	promo_code_id = fields.Many2one('saas.promo.code', string='Applied Promo Code', readonly=True)
	promo_code_discount = fields.Float(string='Promo Discount', readonly=True, help='Discount amount from promo code')
	
	# Auto-renewal preference
	auto_renew = fields.Boolean(string='Auto-Renew Subscription', default=False, help='Automatically renew subscription when it expires')
	
	
	def action_confirm(self):
		"""Override to create subscription when order is confirmed"""
		res = super(SaleOrder, self).action_confirm()
		
		# Create subscription for SaaS orders
		for order in self:
			if order.saas_plan_id and order.saas_company_name:
				order._create_saas_subscription()
			
			# Automatic Invoicing for SaaS orders
			if order.saas_plan_id:
				try:
					# Create invoice
					invoices = order._create_invoices()
					# Post invoice
					for invoice in invoices:
						invoice.action_post()
				except Exception as e:
					_logger.error(f"Failed to auto-invoice SaaS order {order.name}: {str(e)}")
		
		return res
	
	def _create_saas_subscription(self):
		"""Create or Update SaaS subscription from sale order"""
		self.ensure_one()
		
		try:
			# Check if this is an update (Renewal/Upgrade) to an existing subscription
			# Use origin_id if set (explicit), otherwise check if we already created one (idempotency)
			subscription = self.saas_subscription_origin_id or self.saas_subscription_id
			is_update = bool(subscription)
			
			# Determine if early adopter status should be granted (Only for new subs)
			is_early_adopter = False
			if not is_update:
				if self.saas_plan_id.is_early_adopter:
					# Double check limit before confirming
					if not self.saas_plan_id.can_use_early_adopter():
						# Fallback can be implemented here
						is_early_adopter = False
					else:
						is_early_adopter = True
				elif self.promo_code_id and self.promo_code_id.grant_early_adopter:
					is_early_adopter = True
			
			# Calculate Add-ons
			extra_users = 0
			extra_storage = 0
			accounting_module = False
			real_estate_module = False
			
			if is_early_adopter or (is_update and subscription.is_early_adopter):
				accounting_module = True
			
			for line in self.order_line:
				product_code = line.product_id.default_code or ''
				
				# Additional Users
				if product_code == 'SAAS_USER' or product_code == 'SAAS_EXTRA_USER':
					extra_users += int(line.product_uom_qty)
				
				# Additional Storage
				elif product_code.startswith('SAAS_STORAGE_'):
					if '5GB' in product_code:
						extra_storage += 5 * int(line.product_uom_qty)
					elif '10GB' in product_code:
						extra_storage += 10 * int(line.product_uom_qty)
					elif '25GB' in product_code:
						extra_storage += 25 * int(line.product_uom_qty)
				
				# Modules
				elif product_code.startswith('SAAS_ACCOUNTING'):
					accounting_module = True
				elif product_code.startswith('SAAS_REALESTATE'):
					real_estate_module = True
			
			# Bonus storage for additional users (1 GB per user)
			extra_storage += extra_users
			
			if is_update:
				# ── Update existing subscription ──────────────────────────────────────
				vals = {}

				# ── Create saas.addon records for each add-on product in the order ──
				# Proration: (days_remaining / 30) * monthly_price * qty
				# The sale order line price is updated to the prorated amount so the
				# invoice charges exactly the right (prorated) amount this period.
				for line in self.order_line:
					product_code = line.product_id.default_code or ''

					if product_code in ('SAAS_USER', 'SAAS_EXTRA_USER'):
						qty = int(line.product_uom_qty)
						
						# The line price is already strictly monthly (no proration)
						# So the amount actually paid is the line subtotal.
						prorated_total = line.price_subtotal
						
						# The full monthly price comes from the product list price
						per_unit_price = line.product_id.list_price
						
						# Monthly strictly
						
						self.env['saas.addon'].create({
							'subscription_id': subscription.id,
							'addon_type': 'users',
							'quantity': qty,
							'monthly_price': per_unit_price,
							'purchase_date': fields.Date.today(),
							'next_renewal_date': fields.Date.today() + timedelta(days=30),
							'sale_order_id': self.id,
							'order_line_id': line.id,
							'state': 'active',
						})
						_logger.info(
							f'Created user addon: {qty} users @ €{per_unit_price}/u '
							f'for 30 days for {subscription.name}'
						)

					elif product_code.startswith('SAAS_STORAGE_'):
						if '5GB' in product_code:
							gb_per_unit = 5
						elif '10GB' in product_code:
							gb_per_unit = 10
						elif '25GB' in product_code:
							gb_per_unit = 25
						else:
							gb_per_unit = 0

						if gb_per_unit:
							qty = int(line.product_uom_qty)
							total_gb = gb_per_unit * qty
							
							prorated_total = line.price_subtotal
							per_unit_price = line.product_id.list_price

							self.env['saas.addon'].create({
								'subscription_id': subscription.id,
								'addon_type': 'storage',
								'quantity': total_gb,
								'monthly_price': per_unit_price,
								'purchase_date': fields.Date.today(),
								'next_renewal_date': fields.Date.today() + timedelta(days=30),
								'sale_order_id': self.id,
								'order_line_id': line.id,
								'state': 'active',
							})
							_logger.info(
								f'Created storage addon: {total_gb}GB @ €{per_unit_price}/pack '
								f'for 30 days for {subscription.name}'
							)

				# Module enablement (unchanged)
				if accounting_module and not subscription.accounting_module:
					vals['accounting_module'] = True
				if real_estate_module and not subscription.real_estate_module:
					vals['real_estate_module'] = True
				
				# Plan Change (Upgrade)
				if self.saas_plan_id and self.saas_plan_id != subscription.plan_id:
					vals['plan_id'] = self.saas_plan_id.id
					vals['billing_cycle'] = self.saas_billing_cycle
					
					# Reset expiration for Upgrade (Start fresh cycle)
					start_date = fields.Datetime.now()
					if self.saas_billing_cycle == 'annual':
						vals['expiration_date'] = start_date + timedelta(days=365)
					else:
						vals['expiration_date'] = start_date + timedelta(days=30)
					
					_logger.info(f'Subscription {subscription.name} upgraded to {self.saas_plan_id.name}')
				
				# Renewal (Same Plan)
				elif self.saas_plan_id == subscription.plan_id:
					# Check if the Plan Product is in the order -> Extend Main Expiration
					plan_product = subscription.plan_id.product_id
					is_full_renewal = False
					 
					# Check for Add-ons (Users / Storage) in order lines
					# Users/Storage are monthly (as per user request)
					has_users_addon = False
					has_storage_addon = False
					 
					for line in self.order_line:
						code = line.product_id.default_code or ''
						if line.product_id == plan_product:
							is_full_renewal = True
						elif code.startswith('SAAS_USER') or code.startswith('SAAS_EXTRA_USER'):
							has_users_addon = True
						elif code.startswith('SAAS_STORAGE'):
							has_storage_addon = True
					 
					if is_full_renewal:
						
						# Extend expiration
						current_expiry = subscription.expiration_date or fields.Datetime.now()
						# If already expired, start from now
						if current_expiry < fields.Datetime.now():
							current_expiry = fields.Datetime.now()
							
						if self.saas_billing_cycle == 'annual':
							vals['expiration_date'] = current_expiry + timedelta(days=365)
						else:
							vals['expiration_date'] = current_expiry + timedelta(days=30)
							
						_logger.info(f'Subscription {subscription.name} renewed. New Expiry: {vals.get("expiration_date")}')
					 
					# Users add-on: next_renewal_date extension handled via saas.addon records
					if has_users_addon:
						_logger.info(f'Subscription {subscription.name} users addon processed (saas.addon records created above).')
						 
					# Storage add-on: next_renewal_date extension handled via saas.addon records
					if has_storage_addon:
						_logger.info(f'Subscription {subscription.name} storage addon processed (saas.addon records created above).')
					 
					if not is_full_renewal and not has_users_addon and not has_storage_addon:
						_logger.info(f'Subscription {subscription.name} order processed but no extension triggered.')
				if subscription.state != 'active':
					vals['state'] = 'active'
					vals['grace_period_start'] = False
					vals['grace_period_end'] = False

				# Update Auto-Renew preference
				if self.auto_renew:
					vals['auto_renew'] = True
					
				subscription.write(vals)
				
				# Explicitly push the un-suspended status immediately when returning to active
				if vals.get('state') == 'active' and subscription.database_name:
					subscription._push_limits_to_tenant()
					subscription._push_status_to_tenant('active')
				
				# Ensure we link this order to the subscription if not already
				if not self.saas_subscription_id:
					self.write({'saas_subscription_id': subscription.id})
					
			else:
				# Create NEW subscription
				subscription = self.env['saas.subscription'].create({
					'partner_id': self.partner_id.id,
					'company_name': self.saas_company_name,
					'plan_id': self.saas_plan_id.id,
					'billing_cycle': self.saas_billing_cycle or 'monthly',
					'order_id': self.id,
					'state': 'pending',
					'is_early_adopter': is_early_adopter,
					'promo_code_id': self.promo_code_id.id if self.promo_code_id else False,
					'accounting_module': accounting_module,
					'real_estate_module': real_estate_module,
					'auto_renew': self.auto_renew,
				})
				
				self.saas_subscription_id = subscription.id
				
				if self.promo_code_id:
					self.promo_code_id.use_code(self.partner_id.id, subscription.id)
				
				_logger.info(f'Subscription {subscription.name} created from order {self.name}')
				
				# Check and Create Portal User if needed
				if self.partner_id:
					user = self.env['res.users'].search([('partner_id', '=', self.partner_id.id)], limit=1)
					if not user:
						try:
							# Create Portal User
							user = self.env['res.users'].create({
								'name': self.partner_id.name,
								'login': self.partner_id.email,
								'email': self.partner_id.email,
								'partner_id': self.partner_id.id,
								'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
							})
							# Send password reset email (invitation)
							user.action_reset_password()
							_logger.info(f"Created portal user {user.login} for partner {self.partner_id.name}")
						except Exception as e:
							_logger.error(f"Failed to create portal user for {self.partner_id.name}: {e}")
				
				# Auto-provision if enabled
				auto_provision = self.env['ir.config_parameter'].sudo().get_param('saas.auto_provision_on_payment', 'True')
				if auto_provision == 'True':
					# Priority: Try action_provision_tenant (Real Provisioning)
					if hasattr(subscription, 'action_provision_tenant'):
						try:
							subscription.action_provision_tenant()
							_logger.info(f"Auto-provisioned subscription {subscription.name}")
						except Exception as e:
							_logger.error(f"Auto-provisioning failed for {subscription.name}: {e}")
							# Don't raise, as we don't want to rollback sale order confirmation
							
					# Fallback: action_provision_subscription (Mock/Base)
					elif hasattr(subscription, 'action_provision_subscription'):
						subscription.action_provision_subscription()
						_logger.info(f"Auto-provisioned subscription {subscription.name} (Mock)")
		
		except Exception as e:
			_logger.error(f'Failed to process subscription for order {self.name}: {str(e)}')
			# Don't rollback transaction, just log error. 
			# Or should we raise? If we raise, payment confirmation might fail. 
			# Better to log and allow manual fix.
	
	def apply_promo_code(self, promo_code):
		"""Apply promo code to the sale order.
		
		Promo codes grant Early Adopter status to Official plan customers:
		- Official Monthly €59.90 → Early Adopter Monthly €34.90
		- Official Annual €598 → Early Adopter Annual €358
		- Also includes free Accounting module
		"""
		self.ensure_one()
		
		# Check if promo already applied
		if self.promo_code_id:
			return {'success': False, 'message': _('A promo code is already applied. Remove it first to apply a new one.')}
		
		# Check if this is an early adopter plan (promo codes don't work on already discounted plans)
		if self.saas_plan_id and self.saas_plan_id.is_early_adopter:
			return {'success': False, 'message': _('Promo codes cannot be applied to Early Adopter plans (already at Early Adopter pricing).')}
		
		# Find promo code
		promo = self.env['saas.promo.code'].sudo().search([
			('code', '=', promo_code.upper()),
			('active', '=', True)
		], limit=1)
		
		if not promo:
			return {'success': False, 'message': _('Invalid promo code')}
		
		if not promo.can_use():
			return {'success': False, 'message': _('This promo code has expired or reached its usage limit')}
		
		# Only early_adopter type is supported
		if promo.code_type != 'early_adopter':
			return {'success': False, 'message': _('Invalid promo code type')}
		
		# Calculate discount: difference between Official and Early Adopter pricing
		discount_amount = 0.0
		message = ''
		
		if self.saas_billing_cycle == 'monthly':
			# Official Monthly €59.90 → Early Adopter Monthly €34.90
			official_price = self.saas_plan_id.price_monthly
			early_price = self.saas_plan_id.early_adopter_price  # €34.90
			discount_amount = official_price - early_price
			message = f'Early Adopter pricing applied! €{early_price:.2f}/month (was €{official_price:.2f}/month)'
		elif self.saas_billing_cycle == 'annual':
			# Official Annual €598 → Early Adopter Annual €358
			official_price = self.saas_plan_id.price_annual
			# For annual, early_adopter_price stores monthly equivalent (€29.90)
			# The actual annual discount price is stored in early_adopter plan
			early_annual_price = self.saas_plan_id.early_adopter_price * 12  # Approximate
			# But we use the exact configured price from the Early Adopter Annual plan
			early_plan = self.env['saas.plan'].sudo().search([
				('plan_type', '=', 'crm_early'),
				('billing_cycle', '=', 'annual'),
				('active', '=', True)
			], limit=1)
			if early_plan:
				early_annual_price = early_plan.price_annual  # €358
			discount_amount = official_price - early_annual_price
			message = f'Early Adopter pricing applied! €{early_annual_price:.2f}/year (was €{official_price:.2f}/year)'
		
		if discount_amount <= 0:
			return {'success': False, 'message': _('This plan is already at or below Early Adopter pricing')}
		
		# Get or create discount product
		discount_product = self._get_discount_product()
		
		# Create discount line
		self.env['sale.order.line'].create({
			'order_id': self.id,
			'product_id': discount_product.id,
			'name': f'Promo Code: {promo.code} - Early Adopter Discount',
			'product_uom_qty': 1,
			'price_unit': -discount_amount,
			'tax_id': [(5, 0, 0)],  # Remove all taxes
			'is_promo_line': True,
		})
		
		# Store promo code reference
		self.write({
			'promo_code_id': promo.id,
			'promo_code_discount': discount_amount,
		})
		
		return {
			'success': True,
			'message': message,
			'promo_code': promo.code,
			'promo_type': 'Early Adopter',
			'discount_amount': discount_amount,
			'new_total': self.amount_total
		}
	
	def remove_promo_code(self):
		"""Remove applied promo code from the sale order"""
		self.ensure_one()
		
		if not self.promo_code_id:
			return {'success': False, 'message': _('No promo code applied')}
		
		# Remove promo code discount lines
		promo_lines = self.order_line.filtered(lambda l: l.is_promo_line)
		promo_lines.unlink()
		
		# Clear promo code reference
		self.write({
			'promo_code_id': False,
			'promo_code_discount': 0.0,
		})
		
		return {
			'success': True,
			'message': _('Promo code removed'),
			'new_total': self.amount_total
		}
	
	def _get_discount_product(self):
		"""Get or create the discount product for promo codes"""
		discount_product = self.env['product.product'].sudo().search([
			('default_code', '=', 'PROMO_DISCOUNT')
		], limit=1)
		
		if not discount_product:
			discount_product = self.env['product.product'].sudo().create({
				'name': 'Promo Code Discount',
				'default_code': 'PROMO_DISCOUNT',
				'type': 'service',
				'list_price': 0.0,
				'sale_ok': False,
				'purchase_ok': False,
				'invoice_policy': 'order',
			})
		
		return discount_product


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'
	
	is_promo_line = fields.Boolean(string='Is Promo Line', default=False)
