{
    "name": "Remove Odoo from URL and Add Your Brand Name",
    'version': '18.0.1.0.0',
    "author": "Usman Khalid",
    'support': 'usmank123428@gmail.com',
    "summary": "Replace '/odoo' in URL with your own brand name.",
    "description": """
        Remove Odoo from URL and Set Brand Name.
        This module helps you to replace '/odoo' from the browser URL with a custom text (e.g., your brand name).
        Features:
        - Checkbox URL replacement on/off.
        - Set your own replacement text.
        - Works on Odoo 17 and 18
    """,
    "category": "Extra Tools",
    "license": "LGPL-3",
    "price": 4.99,
    "currency": "USD",
    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],
    "depends": ["web", 'base'],
    "application": False,
    "installable": True,
    "data": [
          'data/data.xml',
          'views/res_config_settings_views.xml'
      ],
    "assets": {
        "web.assets_backend": [
            
        ],
    },
    'uninstall_hook': '_uninstall_cleanup',
}
