from . import models

import logging
_logger = logging.getLogger(__name__)

def _setup_module(env):
	# _install_languages(env)
	_rename_payment_methods(env)
	_create_bizum_journal(env)
	_create_card_journal(env)

def _rename_payment_methods(env):
	PaymentMethodLine = env['account.payment.method.line']
	
	rename_map = [
		{'journal_type': 'cash', 'payment_type': 'inbound',  'new_name': 'Cash'},
		{'journal_type': 'cash', 'payment_type': 'outbound', 'new_name': 'Cash'},
		{'journal_type': 'bank', 'payment_type': 'inbound',  'new_name': 'Transfer'},
		{'journal_type': 'bank', 'payment_type': 'outbound', 'new_name': 'Transfer'},
	]
	
	for mapping in rename_map:
		lines = PaymentMethodLine.search([
			('payment_method_id.code', '=', 'manual'),
			('journal_id.type', '=', mapping['journal_type']),
			('payment_type', '=', mapping['payment_type']),
		])
		if lines:
			lines.write({'name': mapping['new_name']})
			_logger.info("Renamed %d payment method lines to '%s'", len(lines), mapping['new_name'])

def _create_bizum_journal(env):
	existing = env['account.journal'].search([('name', '=', 'Bizum')], limit=1)
	if not existing:
		journal = env['account.journal'].create({
			'name': 'Bizum',
			'type': 'bank',
			'code': 'BIZ',
		})
		# Rename the auto-created Manual payment method lines
		env['account.payment.method.line'].search([
			('journal_id', '=', journal.id),
			('payment_method_id.code', '=', 'manual'),
		]).write({'name': 'Bizum'})

def _create_card_journal(env):
	existing = env['account.journal'].search([('name', '=', 'Card')], limit=1)
	if not existing:
		journal = env['account.journal'].create({
			'name': 'Card',
			'type': 'bank',
			'code': 'CARD',
		})
		# Rename the auto-created Manual payment method lines
		env['account.payment.method.line'].search([
			('journal_id', '=', journal.id),
			('payment_method_id.code', '=', 'manual'),
		]).write({'name': 'Card'})

# def _install_languages(env):
# 	"""Activate languages and load all translations automatically."""
	
# 	languages = ['es_ES']  # add whatever languages you need
	
# 	for lang_code in languages:
# 		# Step 1: Activate language if not already active
# 		lang = env['res.lang'].search([
# 			('code', '=', lang_code)
# 		], limit=1)
		
# 		if not lang or not lang.active:
# 			env['res.lang']._activate_lang(lang_code)
# 			_logger.info("Language %s activated", lang_code)
		
# 		# Step 2: Load translations for your custom modules
# 		modules_to_translate = [
# 			'om_account_accountant',  # your module
# 			# add all your custom modules here
# 		]
		
# 		for module_name in modules_to_translate:
# 			module = env['ir.module.module'].search([
# 				('name', '=', module_name),
# 				('state', '=', 'installed'),
# 			], limit=1)
			
# 			if module:
# 				module._update_translations([lang_code])
# 				_logger.info(
# 					"Loaded %s translations for %s",
# 					lang_code, module_name
# 				)


