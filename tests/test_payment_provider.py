# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.azul_webpages import const
from odoo.addons.azul_webpages.tests.common import AzulCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(AzulCommon):

    def test_request_hash_known_vector(self):
        """ Test the request AuthHash against a precomputed vector.

        The vector pins the full algorithm of the PDF (p.65-66): concatenation
        order of the 16 request fields, AuthKey appended at the end of the
        string AND used as HMAC key, UTF-16LE encoding, SHA-512, lowercase hex.
        """
        values = [
            '39038540035',                      # MerchantId
            'Test Shop',                        # MerchantName
            'ECommerce',                        # MerchantType
            '$',                                # CurrencyCode
            'TX-001',                           # OrderNumber
            '1000',                             # Amount
            '000',                              # ITBIS
            'https://example.com/approved',     # ApprovedUrl
            'https://example.com/declined',     # DeclinedUrl
            'https://example.com/cancel',       # CancelUrl
            '0', '', '',                        # UseCustomField1 + label + value
            '0', '', '',                        # UseCustomField2 + label + value
        ]
        self.assertEqual(len(values), len(const.REQUEST_HASH_FIELDS))
        self.assertEqual(
            self.provider._azul_calculate_hash(values),
            'edac1df09a43e0fcfc6aa9c082a7fab955ffd388060528bc96b2ca86e99e8d25'
            '57bfca2e5320c76da989c6003b4847ef045b93183f8196bcff1f625fc4b45238',
        )

    def test_response_hash_known_vector(self):
        """ Test the response AuthHash against a precomputed vector (9 fields
        of the return querystring + AuthKey, PDF p.65). """
        values = [
            'TX-001',            # OrderNumber
            '1000',              # Amount
            'OK1234',            # AuthorizationCode
            '20260704120000',    # DateTime
            '00',                # ResponseCode
            '00',                # IsoCode
            'APROBADA',          # ResponseMessage
            '',                  # ErrorDescription
            '20260704999999',    # RRN
        ]
        self.assertEqual(len(values), len(const.RESPONSE_HASH_FIELDS))
        self.assertEqual(
            self.provider._azul_calculate_hash(values),
            '0e7b6bd50d013b4dc6ed8b6f01f5fe22268cfa03054f693c455ad5cf19ed1da3'
            '3c1d0b52ccb7ff00d05089f1555b8c70e4fb4ed8af4bf358258db31d7b1811ca',
        )

    def test_request_hash_with_odoo_style_reference(self):
        """ Test the request AuthHash with an OrderNumber containing hyphens,
        as produced by standard Odoo references ('S00042-1'). """
        values = [
            '39038540035',                      # MerchantId
            'Test Shop',                        # MerchantName
            'ECommerce',                        # MerchantType
            '$',                                # CurrencyCode
            'S00042-1',                         # OrderNumber (Odoo-style)
            '11800',                            # Amount
            '1800',                             # ITBIS
            'https://example.com/approved',     # ApprovedUrl
            'https://example.com/declined',     # DeclinedUrl
            'https://example.com/cancel',       # CancelUrl
            '0', '', '',                        # UseCustomField1 + label + value
            '0', '', '',                        # UseCustomField2 + label + value
        ]
        self.assertEqual(
            self.provider._azul_calculate_hash(values),
            '5f0d9c5698012121ac60f47efc3432947075bfc16a1756ea541af7e60fe2dc27'
            '55386b02b2c04905647a17a84fefa2e856944ef973a6901e327695ef460fa697',
        )

    def test_response_hash_with_odoo_style_reference(self):
        """ Test the response AuthHash with an OrderNumber containing hyphens. """
        values = [
            'S00042-1',          # OrderNumber (Odoo-style)
            '11800',             # Amount
            'OK1234',            # AuthorizationCode
            '20260704120000',    # DateTime
            '00',                # ResponseCode
            '00',                # IsoCode
            'APROBADA',          # ResponseMessage
            '',                  # ErrorDescription
            '20260704999999',    # RRN
        ]
        self.assertEqual(
            self.provider._azul_calculate_hash(values),
            'adf17b67e4ab3dd73a9451cc4c0ab83d6b61da0519233e9c8681c8f65fa321af'
            '8dac4d7ad4f3f569b21558db12ec9ca45e9abe5024680566dabd2c672bdae030',
        )

    def test_api_url_by_state(self):
        """ Test that the Payment Page URL follows the provider state and the
        manual contingency switch (PDF p.13). """
        self.provider.state = 'test'
        self.assertEqual(
            self.provider._azul_get_api_url(), 'https://pruebas.azul.com.do/PaymentPage/'
        )
        self.provider.state = 'enabled'
        self.assertEqual(
            self.provider._azul_get_api_url(),
            'https://pagos.azul.com.do/PaymentPage/Default.aspx',
        )
        self.provider.azul_use_alternate_url = True
        self.assertEqual(
            self.provider._azul_get_api_url(),
            'https://contpagos.azul.com.do/PaymentPage/Default.aspx',
        )

    def test_default_payment_method_codes(self):
        """ Test that AZUL defaults to the card payment method. """
        self.assertEqual(self.provider._get_default_payment_method_codes(), {'card'})
