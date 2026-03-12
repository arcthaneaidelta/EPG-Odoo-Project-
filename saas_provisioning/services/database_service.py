# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
import subprocess
import os
import logging

_logger = logging.getLogger(__name__)


class SaaSDatabaseService(models.AbstractModel):
    _name = 'saas.database.service'
    _description = 'SaaS Database Management Service'
    
    @api.model
    def create_database(self, db_name, admin_password='admin'):
        """
        Create a new System database
        Works for both localhost and Docker environments
        """
        try:
            _logger.info(f'Creating database: {db_name}')
            
            # Use System's built-in database service
            from odoo.service import db
            
            # Check if database already exists
            if db.exp_db_exist(db_name):
                raise UserError(_('Database %s already exists') % db_name)
            
            # Create database
            db.exp_create_database(
                db_name,
                demo=False,
                lang='en_US',  # or 'es_ES' for Spanish
                user_password=admin_password
            )
            
            _logger.info(f'Database {db_name} created successfully')
            return True
            
        except Exception as e:
            _logger.error(f'Database creation failed for {db_name}: {str(e)}')
            raise UserError(_('Database creation failed: %s') % str(e))
    
    @api.model
    def delete_database(self, db_name, backup=True):
        """
        Delete an System database
        Optionally create backup before deletion
        """
        try:
            _logger.info(f'Deleting database: {db_name}')
            
            from odoo.service import db
            
            # Check if database exists
            if not db.exp_db_exist(db_name):
                _logger.warning(f'Database {db_name} does not exist')
                return True
            
            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = self._backup_database(db_name)
            
            # Delete database
            db.exp_drop(db_name)
            
            _logger.info(f'Database {db_name} deleted successfully')
            return backup_path
            
        except Exception as e:
            _logger.error(f'Database deletion failed for {db_name}: {str(e)}')
            raise UserError(_('Database deletion failed: %s') % str(e))
    
    @api.model
    def _backup_database(self, db_name):
        """Create database backup"""
        try:
            from datetime import datetime
            from odoo.service import db
            
            # Generate backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'{db_name}_{timestamp}.dump'
            
            # Get backup directory from config
            backup_dir = self.env['ir.config_parameter'].sudo().get_param(
                'saas.backup_directory',
                '/tmp/odoo_backups'
            )
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create backup using System's service
            with open(backup_path, 'wb') as backup_file:
                db.exp_dump(db_name, backup_file)
            
            _logger.info(f'Backup created: {backup_path}')
            return backup_path
            
        except Exception as e:
            _logger.error(f'Backup failed for {db_name}: {str(e)}')
            # Don't fail the whole operation if backup fails
            return None
    
    @api.model
    def install_modules(self, db_name, module_list):
        """
        Install modules in a specific database
        """
        try:
            _logger.info(f'Installing modules {module_list} in database {db_name}')
            
            import odoo
            registry = odoo.registry(db_name)
            
            # Switch to target database context
            with registry.cursor() as cr:
                env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                # Install each module
                for module_name in module_list:
                    module = env['ir.module.module'].search([
                        ('name', '=', module_name),
                        ('state', '=', 'uninstalled')
                    ], limit=1)
                    
                    if module:
                        module.button_immediate_install()
                        _logger.info(f'Module {module_name} installed in {db_name}')
                    else:
                        _logger.warning(f'Module {module_name} not found or already installed')
            
            return True
            
        except Exception as e:
            _logger.error(f'Module installation failed in {db_name}: {str(e)}')
            # Don't fail provisioning if module installation fails
            return False
