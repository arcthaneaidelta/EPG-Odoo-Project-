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
        "website_crm"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        # "data/crm_automation.xml",
        "data/mail_templates.xml",
        # 'data/website_crm_data.xml',
    ],
    "application": True,
}
