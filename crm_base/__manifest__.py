{
    "name": "CRM Base - SaaS",
    "summary": "CRM extensions with scoring and automation",
    "version": "1.0",
    "category": "Sales/CRM",
    "depends": [
        "crm",
        "mail",
        "base_automation",
        "website",
        "website_crm",
        "sale_management"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/crm_lead_lost_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        # "data/crm_automation.xml",
        "data/mail_templates.xml",
        "data/menu_order.xml",
    ],
    "application": True,
}
