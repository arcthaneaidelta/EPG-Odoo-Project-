# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
import re
import logging

_logger = logging.getLogger(__name__)


class SaaSProvisioningService(models.AbstractModel):
	_name = 'saas.provisioning.service'
	_description = 'SaaS Tenant Provisioning Service'
	
	@api.model
	def provision_tenant(self, subscription_id):
		"""
		Main provisioning workflow
		Creates database, installs modules, sets up subdomain
		"""
		subscription = self.env['saas.subscription'].browse(subscription_id)
		
		if not subscription:
			raise UserError(_('Subscription not found'))
		
		try:
			# Update status
			subscription.write({
				'provisioning_status': 'in_progress',
				'provisioning_error': False
			})
			
			# Step 1: Generate database name and subdomain
			db_name, subdomain = self._generate_tenant_identifiers(subscription.company_name)
			
			# Step 2: Create database
			db_service = self.env['saas.database.service']
			admin_password = self._generate_secure_password()
			
			db_service.create_database(db_name, admin_password)
			
			# Step 3: Install base modules based on plan
			modules_to_install = self._get_modules_for_plan(subscription.plan_id)
			if modules_to_install:
				db_service.install_modules(db_name, modules_to_install)
			
			# Step 4: Post-Install Configuration (Company Name, etc.)
			self._post_provisioning_setup(db_name, subscription)
			
			# Step 5: Update subscription with tenant info
			subscription.write({
				'database_name': db_name,
				'subdomain': subdomain,
				'state': 'active',
				'provisioning_status': 'completed',
				'admin_password': admin_password,  # Store password
			})
			
			# Step 6: Send welcome email (TODO)
			self._send_welcome_email(subscription, admin_password)
			
			_logger.info(f'Tenant provisioned successfully: {db_name}')
			return True
			
		except Exception as e:
			_logger.error(f'Provisioning failed for subscription {subscription_id}: {str(e)}')
			subscription.write({
				'provisioning_status': 'failed',
				'provisioning_error': str(e),
				'state': 'error',
				'error_message': f'Provisioning failed: {str(e)}'
			})
			raise
	
	@api.model
	def _post_provisioning_setup(self, db_name, subscription):
		"""
		Configure the new tenant database after creation
		"""
		try:
			import odoo
			registry = odoo.registry(db_name)
			
			with registry.cursor() as cr:
				env = api.Environment(cr, odoo.SUPERUSER_ID, {})
				
				# 1. Update Main Company Name
				main_company = env.ref('base.main_company', raise_if_not_found=False)
				if not main_company:
					main_company = env['res.company'].search([], limit=1)
				
				if main_company:
					main_company.name = subscription.company_name
					# Set email/phone from partner if available
					if subscription.partner_id:
						main_company.email = subscription.partner_id.email
						main_company.phone = subscription.partner_id.phone
				
				# 2. Set Admin User Login/Details? (Optional, kept at 'admin' for now)
				
				# 3. Create Technical/SaaS User? (Optional)
				
		except Exception as e:
			_logger.warning(f'Post-provisioning setup failed for {db_name}: {str(e)}')
			# Don't fail the whole process for this

	@api.model
	def delete_tenant(self, subscription_id, backup=True):
		"""
		Delete tenant database and clean up resources
		"""
		subscription = self.env['saas.subscription'].browse(subscription_id)
		
		if not subscription or not subscription.database_name:
			_logger.warning(f'No database to delete for subscription {subscription_id}')
			return True
		
		try:
			db_service = self.env['saas.database.service']
			
			# Delete database (with optional backup)
			backup_path = db_service.delete_database(
				subscription.database_name,
				backup=backup
			)
			
			# Update subscription
			subscription.write({
				'state': 'deleted',
			})
			
			# Log deletion
			subscription.message_post(
				body=_('Tenant deleted. Database: %s. Backup: %s') % (
					subscription.database_name,
					backup_path or 'None'
				)
			)
			
			_logger.info(f'Tenant deleted: {subscription.database_name}')
			return True
			
		except Exception as e:
			_logger.error(f'Tenant deletion failed: {str(e)}')
			raise
	
	@api.model
	def _generate_tenant_identifiers(self, company_name):
		"""
		Generate database name and subdomain from company name
		"""
		# Clean company name: lowercase, remove non-alphanumeric (except hyphens which are valid in subdomains)
		# However, for DB names, underscores are better.
		
		# 1. Generate Subdomain (RFC 1035: a-z, 0-9, -)
		subdomain = company_name.lower().replace(' ', '-')
		subdomain = re.sub(r'[^a-z0-9-]', '', subdomain)
		
		# Remove leading/trailing hyphens
		subdomain = subdomain.strip('-')
		
		# Ensure it starts with a letter (good practice) and is not empty
		if not subdomain or not subdomain[0].isalpha():
			subdomain = 'tenant-' + subdomain
			
		# Get base domain
		base_domain = self.env['ir.config_parameter'].sudo().get_param(
			'saas.base_domain',
			'abc.com'
		)
		
		# 2. Generate Database Name (Postgres safe: a-z, 0-9, _)
		# Use simple mapping from subdomain, replace hyphens with underscores
		db_safe_name = subdomain.replace('-', '_')
		db_name = f'{db_safe_name}_{base_domain.replace(".", "_")}'
		
		# Check for uniqueness and add suffix if needed (excluding deleted subscriptions)
		counter = 1
		original_db_name = db_name
		original_subdomain = subdomain
		
		while self.env['saas.subscription'].search([
			'|',
			('database_name', '=', db_name),
			('subdomain', '=', subdomain),
			('state', '!=', 'deleted')
		], limit=1):
			db_name = f'{original_db_name}_{counter}'
			subdomain = f'{original_subdomain}{counter}'
			counter += 1
		
		return db_name, subdomain
	
	@api.model
	def _get_modules_for_plan(self, plan):
		"""Get list of modules to install based on subscription plan"""
		modules = []
		
		if plan.module_names:
			# Parse comma-separated module names
			modules = [m.strip() for m in plan.module_names.split(',') if m.strip()]
		
		return modules
	
	@api.model
	def _generate_secure_password(self, length=12):
		"""Generate secure random password"""
		import secrets
		import string
		
		alphabet = string.ascii_letters + string.digits + string.punctuation
		password = ''.join(secrets.choice(alphabet) for _ in range(length))
		return password
	
	# @api.model
	# def _send_welcome_email(self, subscription, admin_password):
	#     """Send welcome email to customer with tenant details"""
	#     # TODO: Implement email template
	#     _logger.info(f'Welcome email should be sent to {subscription.partner_id.email}')
	#     pass
	def _send_welcome_email(self, subscription, admin_password):
		"""Send welcome email to customer with tenant details"""

		template = self.env.ref('saas_provisioning.email_template_saas_welcome', raise_if_not_found=False)

		if not template:
			_logger.warning('Welcome email template not found')
			return

		template.with_context(
			admin_password=admin_password
		).send_mail(
			subscription.id,
			force_send=True
		)

		_logger.info(f'Welcome email sent to {subscription.partner_id.email}')






