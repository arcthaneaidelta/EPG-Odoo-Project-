{
    'name': 'Web Navigation Cards',
    'version': '18.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Replace Top Bar dropdowns with a card-based dashboard',
    'depends': ['web', 'base'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'web_navigation_cards/static/src/css/navbar_patch.css',
            'web_navigation_cards/static/src/xml/*.xml',
            'web_navigation_cards/static/src/js/submenu_dashboard.js', 
            'web_navigation_cards/static/src/js/navbar_patch.js',
        ],
    },
    'installable': True,
}