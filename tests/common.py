# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AzulCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.azul = cls._prepare_provider('azul', update_values={
            'azul_merchant_id': '39038540035',
            'azul_merchant_name': 'Test Shop',
            'azul_merchant_type': 'ECommerce',
            'azul_currency_code': '$',
            'azul_auth_key': 'dummy_azul_auth_key_for_tests',
        })
        cls.provider = cls.azul

        cls.currency_dop = cls._prepare_currency('DOP')
        cls.currency = cls.currency_dop
        cls.amount = 10.0
        cls.reference = 'TX-001'

    def _azul_notification_data(self, tx, iso_code='00', **overrides):
        """ Build an AZUL return querystring payload with a valid response hash.

        :param recordset tx: The transaction the notification refers to.
        :param str iso_code: The IsoCode of the simulated response.
        :param dict overrides: Values overriding the default payload (applied
                               before the hash is computed).
        :return: The notification data.
        :rtype: dict
        """
        approved = iso_code == '00'
        data = {
            'OrderNumber': tx.reference,
            'Amount': tx.azul_amount_sent or '1000',
            'ITBIS': tx.azul_itbis_sent or '000',
            'AuthorizationCode': 'OK1234' if approved else '',
            'DateTime': '20260704120000',
            'ResponseCode': 'ISO8583',
            'IsoCode': iso_code,
            'ResponseMessage': 'APROBADA' if approved else 'DECLINADA',
            'ErrorDescription': '' if approved else 'DECLINED BY ISSUER',
            'RRN': '20260704999999',
            'AzulOrderId': '45678',
        }
        data.update(overrides)
        data['AuthHash'] = tx._azul_compute_response_hash(data)
        return data
