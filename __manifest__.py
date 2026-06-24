{
    'name': "installment",

    'author': "Ahmed Elgazzar",

    'category': 'Accounting',
    'version': '0.1',

    'depends': [
        'base',
        'account',
        'mail',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/installment_payment_wizard_view.xml',
        'views/installment_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,

}