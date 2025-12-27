{
    "name": "Website Corporate - SaaS",
    "summary": "Corporate website with CRM lead capture",
    "version": "1.0",
    "category": "Website",
    "depends": [
        "website",
        # "website_form",
        "crm",
        "crm_base",
    ],
    "data": [
        "views/website_templates.xml",
        # "views/website_forms.xml",
        # "data/website_pages.xml",
        "data/website_crm_inherit.xml",
    ],
    "installable": True,
    "application": False,
}
