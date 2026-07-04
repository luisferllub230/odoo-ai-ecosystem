# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

# AZUL Payment Page URLs (PDF "E-Commerce AZUL — Página de Pagos", p.13).
PAYMENT_PAGE_URLS = {
    'test': 'https://pruebas.azul.com.do/PaymentPage/',
    'prod': 'https://pagos.azul.com.do/PaymentPage/Default.aspx',
    'prod_alternate': 'https://contpagos.azul.com.do/PaymentPage/Default.aspx',
}

# Fields of the sale request that participate in the request AuthHash, in the
# exact concatenation order mandated by the PDF (p.65). The AuthKey is appended
# at the end of the string by `_azul_calculate_hash()` (double use of the key:
# end of string + HMAC key, as in both PDF examples, p.66).
REQUEST_HASH_FIELDS = [
    'MerchantId',
    'MerchantName',
    'MerchantType',
    'CurrencyCode',
    'OrderNumber',
    'Amount',
    'ITBIS',
    'ApprovedUrl',
    'DeclinedUrl',
    'CancelUrl',
    'UseCustomField1',
    'CustomField1Label',
    'CustomField1Value',
    'UseCustomField2',
    'CustomField2Label',
    'CustomField2Value',
]

# Fields of the return querystring that participate in the response AuthHash,
# in the exact concatenation order mandated by the PDF (p.65).
RESPONSE_HASH_FIELDS = [
    'OrderNumber',
    'Amount',
    'AuthorizationCode',
    'DateTime',
    'ResponseCode',
    'IsoCode',
    'ResponseMessage',
    'ErrorDescription',
    'RRN',
]

# The only approval code documented by AZUL (PDF p.69). Any other IsoCode is a
# decline or an error.
APPROVED_ISO_CODE = '00'

# The codes of the payment methods to activate when AZUL is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    'card',
}
