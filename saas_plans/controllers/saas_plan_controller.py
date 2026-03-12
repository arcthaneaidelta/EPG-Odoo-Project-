# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import logging
import re

_logger = logging.getLogger(__name__)


class SaaSPlanController(http.Controller):
	
	@http.route('/saas/plans', type='http', auth='public', website=True)
	def saas_plans(self, **kwargs):
		"""Display available SaaS plans"""
		# Get early adopter plans
		early_plans = request.env['saas.plan'].sudo().search([
			('active', '=', True),
			('plan_type', '=', 'crm_early'),
		], order='sequence')
		
		# Get official plans
		official_plans = request.env['saas.plan'].sudo().search([
			('active', '=', True),
			('plan_type', '=', 'crm_official'),
		], order='sequence')
		
		# Get global early adopter count
		global_ea_count = request.env['saas.plan'].sudo().get_global_early_adopter_count()
		ea_limit = 1000
		ea_remaining = max(0, ea_limit - global_ea_count)
		
		return request.render('saas_plans.saas_plans_page', {
			'early_plans': early_plans,
			'official_plans': official_plans,
			'ea_count': global_ea_count,
			'ea_limit': ea_limit,
			'ea_remaining': ea_remaining,
		})
	
	@http.route('/saas/plan/<int:plan_id>/subscribe', type='http', auth='public', website=True)
	def subscribe_to_plan(self, plan_id, **kwargs):
		"""Subscribe to a SaaS plan"""
		plan = request.env['saas.plan'].sudo().browse(plan_id)
		
		if not plan.exists():
			return request.redirect('/saas/plans')
		
		# Create or get sale order
		order = request.website.sale_get_order(force_create=True)
		
		# Store plan info in session for later use
		request.session['saas_plan_id'] = plan_id
		
		return request.render('saas_plans.subscribe_form', {
			'plan': plan,
			'order': order,
		})
	
	@http.route('/saas/plan/checkout', type='http', auth='public', website=True, methods=['POST'])
	def confirm_subscription(self, **post):
		"""Confirm subscription and add to cart"""
		plan_id = request.session.get('saas_plan_id')
		if not plan_id:
			return request.redirect('/saas/plans')
		
		plan = request.env['saas.plan'].sudo().browse(int(plan_id))
		if not plan.exists():
			return request.redirect('/saas/plans')
		
		# Get or create sale order
		order = request.website.sale_get_order(force_create=True)
		
		# Get company name and billing cycle from form
		company_name = post.get('company_name', '')
		billing_cycle = post.get('billing_cycle', plan.billing_cycle)
		auto_renew = post.get('auto_renew', '0') == '1'
		
		if not company_name:
			return request.redirect('/saas/plan/%s/subscribe' % plan_id)
		
		# Store SaaS-specific data in order
		order.write({
			'saas_plan_id': plan.id,
			'saas_company_name': company_name,
			'saas_billing_cycle': billing_cycle,
			'auto_renew': auto_renew,
		})
		
		# Clear existing SaaS lines to rebuild cart
		order.order_line.filtered(lambda l: l.product_id.default_code and 
								  l.product_id.default_code.startswith('SAAS_')).unlink()
		
		# 1. Add Main Plan Product
		product = self._create_plan_product(plan, billing_cycle)
		order._cart_update(
			product_id=product.id,
			line_id=None,
			add_qty=1,
		)
		
		# Helper to add product by code
		def add_product_by_code(code, qty=1, price_unit=None, name_override=None):
			prod = request.env['product.product'].sudo().search([('default_code', '=', code)], limit=1)
			if prod:
				line_values = {'product_uom_qty': qty}
				if price_unit is not None:
					line_values['price_unit'] = price_unit
				if name_override:
					line_values['name'] = name_override
					
				# _cart_update allows passing set_quantity and other kwargs that might set price?
				# Standard _cart_update doesn't easily allow setting price_unit directly in the call 
				# unless we write to the line afterwards.
				res = order._cart_update(
					product_id=prod.id,
					line_id=None,
					add_qty=qty,
				)
				line_id = res.get('line_id')
				if line_id and (price_unit is not None or name_override):
					line = request.env['sale.order.line'].sudo().browse(line_id)
					vals = {}
					if price_unit is not None:
						vals['price_unit'] = price_unit
					if name_override:
						vals['name'] = name_override
					line.write(vals)

		# 2. Add Accounting Module
		if post.get('addon_accounting') == '1':
			acc_code = 'SAAS_ACCOUNTING_MONTHLY' if billing_cycle == 'monthly' else 'SAAS_ACCOUNTING_ANNUAL'
			if plan.is_early_adopter:
				# Free for Early Adopters
				add_product_by_code(acc_code, price_unit=0.0, name_override='Accounting Module (Included Free)')
			else:
				# Paid for Official
				add_product_by_code(acc_code)
				
		# 3. Add Real Estate Module
		if post.get('addon_real_estate') == '1':
			re_code = 'SAAS_REALESTATE_MONTHLY' if billing_cycle == 'monthly' else 'SAAS_REALESTATE_ANNUAL'
			add_product_by_code(re_code)
			
		# 4. Add Additional Users
		extra_users = int(post.get('extra_users', '0'))
		if extra_users > 0:
			add_product_by_code('SAAS_EXTRA_USER', qty=extra_users)
			
		# 5. Add Storage Expansion
		storage_expansion = int(post.get('storage_expansion', '0'))
		if storage_expansion in [5, 10, 25]:
			storage_code = f'SAAS_STORAGE_{storage_expansion}GB'
			add_product_by_code(storage_code)
		
		return request.redirect('/shop/checkout')
	
	def _create_plan_product(self, plan, billing_cycle):
		"""Create or get product for a SaaS plan"""
		# First, check if plan has a linked product
		if plan.product_id:
			return plan.product_id
		
		# Fallback: create dynamic product
		product_code = f'SAAS_{plan.id}_{billing_cycle.upper()}'
		
		# Check if product already exists
		product = request.env['product.product'].sudo().search([
			('default_code', '=', product_code)
		], limit=1)
		
		if product:
			return product
		
		# Determine price based on billing cycle
		if billing_cycle == 'monthly':
			price = plan.price_monthly
			name = f'{plan.name} - Monthly'
		else:
			price = plan.price_annual
			name = f'{plan.name} - Annual'
		
		# Create product
		product = request.env['product.product'].sudo().create({
			'name': name,
			'default_code': product_code,
			'type': 'service',
			'list_price': price,
			'sale_ok': True,
			'purchase_ok': False,
			'invoice_policy': 'order',
			'categ_id': request.env.ref('product.product_category_all').id,
			'is_published': True,
		})
		
		return product
	
	@http.route('/saas/apply_promo_code', type='json', auth='public', website=True)
	def apply_promo_code(self, promo_code):
		"""Apply promo code to current sale order"""
		try:
			# Get current sale order from session
			order_id = request.session.get('sale_order_id')
			if not order_id:
				return {'success': False, 'message': _('No active order found')}
			
			order = request.env['sale.order'].sudo().browse(order_id)
			if not order.exists():
				return {'success': False, 'message': _('Order not found')}
			
			# Apply promo code (check is done in the model method)
			result = order.apply_promo_code(promo_code)
			return result
			
		except Exception as e:
			_logger.error(f'Error applying promo code: {str(e)}')
			return {'success': False, 'message': _('An error occurred while applying the promo code')}
	
	@http.route('/saas/remove_promo_code', type='json', auth='public', website=True)
	def remove_promo_code(self):
		"""Remove promo code from current sale order"""
		try:
			# Get current sale order from session
			order_id = request.session.get('sale_order_id')
			if not order_id:
				return {'success': False, 'message': _('No active order found')}
			
			order = request.env['sale.order'].sudo().browse(order_id)
			if not order.exists():
				return {'success': False, 'message': _('Order not found')}
			
			# Remove promo code
			result = order.remove_promo_code()
			return result
			
		except Exception as e:
			_logger.error(f'Error removing promo code: {str(e)}')
			return {'success': False, 'message': _('An error occurred while removing the promo code')}
	
	@http.route('/saas/check_company_name', type='json', auth='public', website=True)
	def check_company_name(self, company_name):
		"""Check if company name/subdomain is available"""
		try:
			# Generate subdomain from company name
			subdomain = company_name.lower().replace(' ', '').replace('-', '')
			
			# Remove special characters
			subdomain = re.sub(r'[^a-z0-9]', '', subdomain)
			
			if not subdomain:
				return {
					'available': False,
					'subdomain': 'invalid',
					'message': 'Please enter a valid company name'
				}
			
			# Check if subdomain already exists in subscriptions (exclude deleted)
			existing = request.env['saas.subscription'].sudo().search([
				('subdomain', '=', subdomain),
				('state', '!=', 'deleted')
			], limit=1)
			
			if existing:
				return {
					'available': False,
					'subdomain': subdomain,
					'message': 'This company name is already taken. Please choose another.'
				}
			
			return {
				'available': True,
				'subdomain': subdomain,
				'message': 'Available!'
			}
			
		except Exception as e:
			_logger.error(f'Error checking company name: {str(e)}')
			return {
				'available': True,  # Allow submission on error
				'subdomain': company_name.lower().replace(' ', ''),
				'message': 'Unable to verify availability'
			}
	@http.route('/my/subscription', type='http', auth='user', website=True)
	def my_subscription(self, **kwargs):
		"""Display user's subscription details (Logged in user)"""
		partner = request.env.user.partner_id
		subscription = request.env['saas.subscription'].sudo().search([
			('partner_id', '=', partner.id),
			('state', 'in', ['active', 'suspended', 'grace_period'])
		], limit=1)
		
		if not subscription:
			return request.render('portal.portal_layout', {
				'page_name': 'subscription',
				'error': 'No active subscription found.'
			})
			
		return request.render('saas_plans.portal_my_subscription', {
			'subscription': subscription,
			'page_name': 'subscription',
		})
	
	@http.route('/saas/manage', type='http', auth='public', website=True)
	def manage_subscription(self, token=None, **kwargs):
		"""Display subscription details via Access Token (No login required)"""
		if not token:
			# Check session
			token = request.session.get('saas_subscription_token')
			
		if not token:
			 return request.redirect('/saas/plans')
			
		subscription = request.env['saas.subscription'].sudo().search([
			('access_token', '=', token)
		], limit=1)
		
		if not subscription:
			return request.render('website.http_error', {
				'status_code': '404',
				'status_message': _('Invalid or expired subscription token.')
			})
		
		# Store token in session for subsequent actions (like upgrade)
		request.session['saas_subscription_token'] = token
		
		return request.render('saas_plans.portal_my_subscription', {
			'subscription': subscription,
			'page_name': 'subscription',
		})

	@http.route('/saas/upgrade', type='http', auth='public', website=True, methods=['POST'])
	def upgrade_subscription(self, **post):
		"""Handle subscription upgrade request"""
		_logger.info("Upgrade Request POST: %s", post)
		
		sub_id = post.get('subscription_id')
		token_from_post = post.get('access_token')
		
		add_users = int(post.get('add_users', 0))
		add_storage = int(post.get('add_storage', 0))
		
		subscription = None
		
		# 1. Try to get subscription by ID if logged in or token is in session
		if sub_id:
			sub = request.env['saas.subscription'].sudo().browse(int(sub_id))
			if sub.exists():
				# if sub.exists():
				# Check ownership: Either logged in user owns it, OR token matches
				
				# Check token from session OR post
				session_token = request.session.get('saas_subscription_token')
				token = token_from_post or session_token
				
				_logger.info("Checking Token. Post: %s, Session: %s, Sub Token: %s", token_from_post, session_token, sub.access_token)
				
				is_owner = False
				if request.env.user._is_public():
					if token and sub.access_token == token:
						is_owner = True
				else:
					# Logged in: Check partner OR token (if admin/testing)
					if sub.partner_id == request.env.user.partner_id:
						is_owner = True
					elif token and sub.access_token == token:
						is_owner = True
						
				if is_owner:
					subscription = sub
		
		if not subscription:
			_logger.warning("Upgrade Failed: Subscription not found or authorized.")
			return request.redirect('/saas/manage')

		# Create upgrade order
		order = request.website.sale_get_order(force_create=True)
		
		_logger.info("Creating Upgrade Order %s for Subscription %s", order.name, subscription.name)
		
		# Link order to subscription
		order.sudo().write({
			'saas_subscription_id': subscription.id,
			'saas_plan_id': subscription.plan_id.id, # Keep same plan
			'saas_company_name': subscription.company_name,
			'partner_id': subscription.partner_id.id, # Link order to correct partner
		})
		
		# Helper to add product
		def add_product(code, qty, price=None):
			product = request.env['product.product'].sudo().search([('default_code', '=', code)], limit=1)
			if product:
				order._cart_update(
					product_id=product.id, 
					add_qty=qty,
					line_id=None
				)
			else:
				_logger.error("Product with code %s not found!", code)

		# Add Users
		if add_users > 0:
			add_product('SAAS_EXTRA_USER', add_users)
			
		# Add Storage
		if add_storage > 0:
			storage_code = f'SAAS_STORAGE_{add_storage}GB'
			add_product(storage_code, 1)
			
		return request.redirect('/shop/checkout')
