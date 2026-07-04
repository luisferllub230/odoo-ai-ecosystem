# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class AzulController(http.Controller):
    _approved_url = '/payment/azul/return/approved'
    _declined_url = '/payment/azul/return/declined'
    _cancel_url = '/payment/azul/return/cancel'

    @http.route(
        [_approved_url, _declined_url], type='http', methods=['GET'], auth='public'
    )
    def azul_return_from_checkout(self, **data):
        """ Process the response sent by AZUL in the return querystring.

        The approved/declined routes share this handler on purpose: the route
        never decides the transaction state; only the hash-verified IsoCode
        does. A manipulated redirection to the "approved" URL with a declined
        IsoCode or an invalid hash can never mark the transaction as paid.

        :param dict data: The notification data (response querystring of AZUL
                          plus our own `reference` and `access_token`).
        :return: A redirection to the payment status page.
        """
        _logger.info(
            "Handling redirection from AZUL with data:\n%s",
            pprint.pformat({
                key: '***' if key == 'access_token' else value for key, value in data.items()
            }),
        )

        # Find the transaction and verify the origin of the return before any
        # state change: our own access token first, then the AZUL response hash.
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'azul', data
        )
        self._verify_return_access_token(data, tx_sudo)
        self._verify_response_hash(data, tx_sudo)

        # Handle the (authenticated) notification data. The framework state
        # machine guarantees idempotency: a duplicated return never re-processes
        # a transaction that already reached a final state.
        tx_sudo._handle_notification_data('azul', data)
        return request.redirect('/payment/status')

    @http.route(_cancel_url, type='http', methods=['GET'], auth='public')
    def azul_return_from_cancel(self, reference=None, access_token=None, **kwargs):
        """ Process the cancellation return of the AZUL Payment Page.

        AZUL calls CancelUrl without any parameter (PDF p.15); only our own
        `reference` and `access_token` embedded in the URL are available.

        :param str reference: The transaction reference embedded in CancelUrl.
        :param str access_token: The access token embedded in CancelUrl.
        :return: A redirection to the payment status page.
        """
        _logger.info("Handling cancellation from AZUL for reference %s.", reference)

        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'azul', {'OrderNumber': reference}
        )
        if not payment_utils.check_access_token(access_token, reference):
            _logger.warning("Received AZUL cancellation with invalid access token.")
            raise Forbidden()

        tx_sudo._handle_notification_data('azul', {'OrderNumber': reference, 'azul_cancel': True})
        return request.redirect('/payment/status')

    @staticmethod
    def _verify_return_access_token(data, tx_sudo):
        """ Check that the access token embedded in the return URL is valid.

        :param dict data: The notification data.
        :param recordset tx_sudo: The sudoed transaction referenced by the
                                  notification data, as a `payment.transaction` record.
        :return: None
        :raise Forbidden: If the access token is missing or invalid.
        """
        access_token = data.get('access_token')
        if not payment_utils.check_access_token(access_token, tx_sudo.reference):
            _logger.warning("Received AZUL return with missing or invalid access token.")
            raise Forbidden()

    @staticmethod
    def _verify_response_hash(data, tx_sudo):
        """ Check that the received response hash matches the expected one.

        The verification is strict: a missing or invalid AuthHash rejects the
        return without touching the transaction state. The querystring is the
        only confirmation channel of the AZUL Payment Page (no webhook), so the
        HMAC is the only proof of integrity and origin.

        :param dict data: The notification data.
        :param recordset tx_sudo: The sudoed transaction referenced by the
                                  notification data, as a `payment.transaction` record.
        :return: None
        :raise Forbidden: If the hash is missing or invalid.
        """
        received_hash = data.get('AuthHash')
        if not received_hash:
            _logger.warning("Received AZUL return with missing AuthHash.")
            raise Forbidden()

        expected_hash = tx_sudo._azul_compute_response_hash(data)
        if not hmac.compare_digest(received_hash.lower(), expected_hash):
            _logger.warning("Received AZUL return with invalid AuthHash.")
            raise Forbidden()
