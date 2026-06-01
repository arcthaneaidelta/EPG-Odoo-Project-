# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import threading
import logging

_logger = logging.getLogger(__name__)

class SaasUpgradeWizard(models.TransientModel):
    _name = 'saas.upgrade.wizard'
    _description = 'Upgrade Tenant Modules'

    module_names = fields.Char(string='Modules to Upgrade', required=True, default='saas_client', help="Comma-separated list of technical module names (e.g., saas_client,crm)")

    def action_upgrade(self):
        active_ids = self.env.context.get('active_ids', [])
        subscriptions = self.env['saas.subscription'].browse(active_ids).filtered(lambda s: s.database_name)
        
        db_names = subscriptions.mapped('database_name')
        modules = [m.strip() for m in self.module_names.split(',')]
        
        if not db_names or not modules:
            return {'type': 'ir.actions.act_window_close'}

        # Run upgrade in a background thread to prevent UI blocking
        thread = threading.Thread(target=self._upgrade_thread, args=(db_names, modules))
        thread.start()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upgrade Started'),
                'message': _('Modules %s are being upgraded on %d tenant databases in the background.') % (self.module_names, len(db_names)),
                'type': 'success',
                'sticky': False,
            }
        }

    def _upgrade_thread(self, db_names, modules):
        import odoo
        for db_name in db_names:
            _logger.info("Starting background upgrade for db %s with modules %s", db_name, modules)
            try:
                registry = odoo.registry(db_name)
                with registry.cursor() as cr:
                    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                    mods = env['ir.module.module'].search([
                        ('name', 'in', modules),
                        ('state', '=', 'installed')
                    ])
                    if mods:
                        mods.button_immediate_upgrade()
                        _logger.info("Successfully upgraded %s on %s", mods.mapped('name'), db_name)
                    else:
                        _logger.warning("No matching installed modules found to upgrade on %s", db_name)
            except Exception as e:
                _logger.error("Failed to upgrade modules on %s: %s", db_name, str(e))
