{
    'name': 'CRM File Management',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Manage opportunities as files with checklists, documents, and tasks',
    'depends': ['crm', 'mail', 'sales_team', 'dms'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_lead_to_file_wizard_views.xml',
        'data/crm_file_stage_data.xml',
        'views/crm_file_stage_views.xml',
        'views/crm_file_type_views.xml',
        'views/crm_file_views.xml',
        'views/crm_lead_views.xml',
        'views/dms_file_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'crm_file_management/static/src/css/crm_file.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
