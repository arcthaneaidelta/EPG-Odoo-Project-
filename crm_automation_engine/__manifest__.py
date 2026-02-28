# -*- coding: utf-8 -*-
{
    'name': 'CRM Automation Engine',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Automated CRM actions using base.automation — zero Python overrides',
    'description': """
CRM Automation Engine
=====================
Provides event-driven automations for:
- Lead management (cold alerts, conversion tracking)
- Sales pipeline (quote follow-up, acceptance, rejection)
- Invoicing (auto-send, overdue alerts, payment tracking)
- Client lifecycle (inactivity detection)
- Temporal events (month/quarter start/end)

All automations use base.automation XML records (no Python overrides).
Fully compatible with multi-module SaaS tenant deployments.
    """,
    'author': 'SaaS Platform',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'sale_management',
        'account',
        'mail',
        'base_automation',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views (must come before data so menu items exist)
        'views/automation_log_views.xml',
        'views/automation_config_views.xml',
        'views/automation_company_views.xml',
        'views/crm_health_report_views.xml',

        # Mail Templates (must come before automations that reference them)
        'data/mail_templates.xml',

        # Automations
        'data/lead_automations.xml',
        'data/sale_automations.xml',
        'data/invoice_automations.xml',
        'data/client_automations.xml',
        'data/temporal_crons.xml',
        'data/crm_health_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
