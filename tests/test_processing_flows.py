# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.azul_webpages.controllers.main import AzulController
from odoo.addons.azul_webpages.tests.common import AzulCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(AzulCommon, PaymentHttpCommon):

    def _azul_return_params(self, tx, **kwargs):
        """ Build the full return querystring: AZUL response + own URL params. """
        data = self._azul_notification_data(tx, **kwargs)
        data['reference'] = tx.reference
        data['access_token'] = self._generate_test_access_token(tx.reference)
        return data

    def _azul_get(self, url, params):
        """ Make a GET request and invalidate the cache to read fresh values. """
        response = self._make_http_get_request(url, params=params)
        self.env.invalidate_all()
        return response

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_approved_return_confirms_transaction(self):
        """ Test that a hash-valid approved return confirms the transaction. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)

        response = self._azul_get(url, self._azul_return_params(tx))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, '45678')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_declined_data_on_approved_route_never_done(self):
        """ Test that a declined IsoCode reaching the *approved* route never
        marks the transaction as paid: only the hash-verified IsoCode decides. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)

        self._azul_get(url, params=self._azul_return_params(tx, iso_code='05'))

        self.assertEqual(tx.state, 'error')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_invalid_response_hash_is_rejected(self):
        """ Test that an invalid response hash is rejected without touching the
        transaction state. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)
        params = self._azul_return_params(tx)
        params['AuthHash'] = 'a' * 128  # Tampered hash.

        response = self._azul_get(url, params=params)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, 'draft')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_missing_response_hash_is_rejected(self):
        """ Test that a return without AuthHash is rejected (strict verification). """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)
        params = self._azul_return_params(tx)
        del params['AuthHash']

        response = self._azul_get(url, params=params)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, 'draft')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_invalid_access_token_is_rejected(self):
        """ Test that a return with an invalid own access token is rejected. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)
        params = self._azul_return_params(tx)
        params['access_token'] = 'invalid-token'

        response = self._azul_get(url, params=params)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, 'draft')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_duplicate_return_does_not_reprocess(self):
        """ Test that a duplicated return GET does not re-process the
        transaction (idempotency). """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        url = self._build_url(AzulController._approved_url)
        params = self._azul_return_params(tx)

        self._azul_get(url, params=params)
        self.assertEqual(tx.state, 'done')
        response = self._azul_get(url, params=params)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_cancel_with_valid_token_cancels_transaction(self):
        """ Test that the cancellation return with a valid own token cancels the
        transaction. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(AzulController._cancel_url)

        response = self._azul_get(url, params={
            'reference': tx.reference,
            'access_token': self._generate_test_access_token(tx.reference),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(tx.state, 'cancel')

    @mute_logger('odoo.addons.azul_webpages.controllers.main')
    def test_cancel_with_invalid_token_is_rejected(self):
        """ Test that a cancellation with an invalid token does not touch the
        transaction. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(AzulController._cancel_url)

        response = self._azul_get(url, params={
            'reference': tx.reference,
            'access_token': 'invalid-token',
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, 'draft')
