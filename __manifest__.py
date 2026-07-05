# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: AZUL Payment Page",
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Dominican payment provider (AZUL Payment Page, browser redirect flow).",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'author': "Luis Fernández",
    'license': 'LGPL-3',
    'depends': ['payment'],
    'data': [
        'views/payment_azul_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',

        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'azul_webpages/static/src/js/payment_form.js',
        ],
    },
    'demo': [
        'demo/payment_provider_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
