# -*- coding: utf-8 -*-
{
    'name': 'SaaS Client Agent',
    'version': '1.0',
    'category': 'SaaS',
    'summary': 'Enforces resource limits on tenant databases',
    'description': """
        SaaS Client Agent
        =================
        
        Installed on Tenant Databases to:
        * Enforce User Limits (saas.max_users)
        * Enforce Storage Limits (saas.max_storage_mb)
        
        This module reads limits from System Parameters (ir.config_parameter), 
        which are managed by the SaaS Manager.
    """,
    'author': 'Your Company',
    'website': 'https://abc.com',
    'depends': ['base', 'odoo_url_replacer'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/login_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
