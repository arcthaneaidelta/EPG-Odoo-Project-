{
    "name": "Dashboard",
    "summary": "Modern sales and finance analytics dashboard",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["crm", "web"],
    "data": [
        "views/dashboard_menu.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "assets": {
        "web.assets_backend": [
            "dashboard/static/src/css/dashboard.css",
            "dashboard/static/src/xml/dashboard_templates.xml",
            "dashboard/static/src/js/dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
}
