# Part of System. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pago por Redsys / Bizum',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Integra la pasarela de pagos de redsys en tu System para pagos con tarjeta de crédito / débito y Bizum',
    'description': """Addon para integrar la pasarela de pagos de redsys con System. Además de integrar Bizum en System.""",
    'author': "Diego T.",
    'sequence': -100,
    'support':"soporte@garber.es",
    'website': "http://www.garber.es",
    'price': '59.99',
    'currency': 'EUR',
    'images': ['static/description/app_image.png'],
    'depends': ['website_sale', 'payment'],
    'data': [
        'views/pay_views.xml',
        'views/pay_redsys.xml',
        'data/pay_provider.xml',
    ],
    "external_dependencies": {
        "python": [
            #"pycryptodome",
        ],
    },
    'application': True,
    'license': 'OPL-1',
}
