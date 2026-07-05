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
        string AND used as HMAC key, message in UTF-16LE, key in raw bytes,
        SHA-512, lowercase hex.
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
            'f9529e7d7b02b317c65639ef063798efef1424aff62fa2335561bdb815fb6470'
            'f0446e1064c1c05f7eb619bfd6bcb0709ebde5fd4a737a083d7f5db1bdd5512f',
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
            '393dfeb863c55d03b54882edf2be10ff5ee4fa4add98b2f7386d19db51f6b2af'
            '42592cdba7ed2165b712ab425a4d53370f58a05d5544dee052aca24a0f9ec5e7',
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
            '106c358633c26a16506aad0b0bb3a0afa5435187002edde3b6ab6db6709f5002'
            'e8ebcef90a8b8cb5592af4853591ab863c67683c8374c1d15fead5cf4f88021f',
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
            '26e09f9ae2e6e924482d8ceff10a0ca765643b60349aadf56a5834cd5225da4b'
            '5418f9f7099eaefbc78027f61a0bc67303300cb522cb8eeae2b244353b36b4f5',
        )

    def test_hash_key_encoding_is_raw_not_utf16le(self):
        """ Guard against the AuthHash regression that AZUL rejects with
        `INVALID_AUTH:AuthHash`: the HMAC key must be the raw bytes of the
        AuthKey, never a UTF-16LE re-encoding (only the message is UTF-16LE,
        PDF PHP example p.66). """
        import hashlib
        import hmac

        auth_key = self.provider.azul_auth_key
        values = ['a', 'b', 'c']
        message = ''.join(values) + auth_key

        wrong = hmac.new(
            auth_key.encode('utf-16-le'), message.encode('utf-16-le'), hashlib.sha512
        ).hexdigest()

        self.assertNotEqual(
            self.provider._azul_calculate_hash(values), wrong,
            "The HMAC key must not be UTF-16LE encoded (AZUL rejects that hash).",
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
