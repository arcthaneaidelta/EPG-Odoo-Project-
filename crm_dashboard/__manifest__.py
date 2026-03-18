{
    "name": "CRM Dashboard",
    "summary": "Custom CRM dashboard with dark blue analytics layout",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["crm", "web"],
    "data": [
        "views/crm_dashboard_menu.xml",
        # "data/menu_order.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "assets": {
        "web.assets_backend": [
            "crm_dashboard/static/src/css/crm_dashboard.css",
            "crm_dashboard/static/src/xml/crm_dashboard_templates.xml",
            "crm_dashboard/static/src/js/crm_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
}
