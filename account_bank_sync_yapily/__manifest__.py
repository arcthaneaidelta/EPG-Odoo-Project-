{
    'name': 'Yapily Bank Synchronization',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Synchronize Bank Statements using Yapily PSD2 API',
    'description': """
        This module integrates the Yapily API to fetch bank transactions automatically.
        Features:
        - PSD2 Bank Authentication via Yapily
        - Account Mapping
        - Automatic Bank Statement Synchronization
        - Manual Fetch support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/account_journal_views.xml',
        'wizard/yapily_connect_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
