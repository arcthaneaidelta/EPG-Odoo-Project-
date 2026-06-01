# -*- coding: utf-8 -*-
{
    'name': 'Real Estate CRM',
    'version': '18.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Complete Real Estate Management integrated with CRM',
    'description': """
        Real Estate CRM Module for Multi-tenant SaaS
        =============================================
        
        This module provides complete real estate management functionality:
        
        Phase 1 Features (Implemented):
        * Property Management (sale & rental)
        * CRM Integration (no parallel CRM)
        * Real Estate Sales Pipeline
        * Rental Contract Management
        * Automatic Recurring Invoicing for Rentals
        * Visit Scheduling and Tracking
        * Automatic Commission Calculation
        * MLS Portal Preparation (technical structure)
        
        Multi-tenant Compatible:
        * Full company isolation (company_id on all models)
        * SaaS-ready architecture
        * Uses core System models (crm.lead, account.move, res.partner)
        * No duplicate logic
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'crm',
        'sale_management',
        'account',
        'calendar',
        'sales_team',
    ],
    'data': [
        # Security
        'security/real_estate_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/real_estate_data.xml',
        'data/ir_cron_data.xml',
        
        # Views - Properties
        'views/real_estate_property_views.xml',
        'views/real_estate_property_type_views.xml',
        
        # Views - Rentals
        'views/real_estate_rental_contract_views.xml',
        
        # Views - Visits
        'views/real_estate_visit_views.xml',
        
        # Views - Commissions
        'views/real_estate_commission_views.xml',
        
        # Views - CRM Extensions
        'views/crm_lead_views.xml',
        
        # Views - Partner Extensions
        'views/res_partner_views.xml',
        
        # Reports
        'report/real_estate_reports.xml',
        'report/property_report_template.xml',
        'report/commission_report_template.xml',
        
        # Menus
        'views/real_estate_menus.xml',
    ],
    'demo': [
        'demo/real_estate_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
