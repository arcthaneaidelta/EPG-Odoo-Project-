# -*- coding: utf-8 -*-
{
    'name': 'CRM Client Kanban - Dark Profile Cards',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'Beautiful dark-themed client kanban cards with sales, invoice, call & meeting stats',
    'description': """
        Adds a standalone "Client Profiles" kanban view under Contacts with rich dark-themed
        profile cards showing total sales, invoices, calls, and meetings per client.
        Does NOT inherit or modify the base res.partner kanban view, avoiding conflicts
        with calendar, crm, sale, and pos modules that target //footer/div.
    """,
    'author': 'Custom',
    'depends': [
        'base',
        'contacts',        # contacts_menu_root + res.partner views
        'sale_management', # sale.order for total sales
        'account',         # account.move for invoice count
        'crm',             # action_new_opportunity on res.partner
        'calendar',        # calendar.event for meeting count
        'sales_team',      # group_sale_salesman for New Deal button guard
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_client_kanban/static/src/scss/client_kanban.scss',
            'crm_client_kanban/static/src/js/client_kanban.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
