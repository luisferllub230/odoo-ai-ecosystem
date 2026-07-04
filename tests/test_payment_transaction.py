# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.azul_webpages import const
from odoo.addons.azul_webpages.tests.common import AzulCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(AzulCommon):

    def test_rendering_values(self):
        """ Test that the rendering values use the exact POST field names of the
        PDF, the minor-units amount format and the test Payment Page URL. """
        tx = self._create_transaction(flow='redirect')  # 10.00 DOP
        rendering_values = tx._get_specific_rendering_values(None)

        expected_field_names = set(const.REQUEST_HASH_FIELDS) | {'Locale', 'AuthHash', 'api_url'}
        self.assertEqual(set(rendering_values), expected_field_names)
        self.assertEqual(rendering_values['MerchantId'], '39038540035')
        self.assertEqual(rendering_values['MerchantName'], 'Test Shop')
        self.assertEqual(rendering_values['MerchantType'], 'ECommerce')
        self.assertEqual(rendering_values['CurrencyCode'], '$')
        self.assertEqual(rendering_values['OrderNumber'], tx.reference)
        self.assertEqual(rendering_values['Amount'], '1000')  # 10.00 DOP
        self.assertEqual(rendering_values['ITBIS'], '000')  # No linked documents.
        self.assertEqual(rendering_values['UseCustomField1'], '0')
        self.assertEqual(rendering_values['UseCustomField2'], '0')
        self.assertEqual(rendering_values['Locale'], 'EN')  # Partner lang is en_US.
        self.assertEqual(
            rendering_values['api_url'], 'https://pruebas.azul.com.do/PaymentPage/'
        )
        for url_field in ('ApprovedUrl', 'DeclinedUrl', 'CancelUrl'):
            self.assertIn('/payment/azul/return/', rendering_values[url_field])
            self.assertIn('access_token=', rendering_values[url_field])
        # The hash covers the 16 request fields in the documented order.
        self.assertEqual(
            rendering_values['AuthHash'],
            self.provider._azul_calculate_hash(
                [rendering_values[field_name] for field_name in const.REQUEST_HASH_FIELDS]
            ),
        )
        # The values sent are documented on the transaction.
        self.assertEqual(tx.azul_amount_sent, '1000')
        self.assertEqual(tx.azul_itbis_sent, '000')
        self.assertFalse(tx.azul_conversion_details)  # No conversion for DOP.

    def _set_dop_rate(self, rate, company=None):
        """ Create an explicit DOP rate (units of DOP per 1 company currency). """
        return self.env['res.currency.rate'].create({
            'currency_id': self.currency_dop.id,
            'rate': rate,
            'name': fields.Date.context_today(self.env.user),
            'company_id': (company or self.env.company).id,
        })

    def test_rendering_values_convert_to_dop_golden_rate(self):
        """ Test the USD -> DOP conversion against exact golden numbers:
        1 USD = 60.5 DOP, 10.00 USD must yield Amount '60500'. """
        if self.env.company.currency_id != self.currency_usd:
            self.skipTest("company currency is not USD")
        self._set_dop_rate(60.5)
        tx = self._create_transaction(
            flow='redirect', currency_id=self.currency_usd.id, reference='TX-USD-001'
        )
        rendering_values = tx._get_specific_rendering_values(None)

        self.assertEqual(rendering_values['Amount'], '60500')  # 10.00 * 60.5 = 605.00 DOP
        self.assertNotEqual(
            rendering_values['Amount'],
            str(payment_utils.to_minor_currency_units(tx.amount, self.currency_usd)),
            "The amount sent to AZUL must be converted, not the raw USD amount.",
        )
        self.assertEqual(rendering_values['CurrencyCode'], '$')  # Always the DOP MID code.
        self.assertTrue(tx.azul_conversion_details)
        self.assertIn('USD', tx.azul_conversion_details)
        self.assertIn('DOP', tx.azul_conversion_details)

    def test_rendering_values_conversion_subcent_rounding(self):
        """ Test the rounding chain on a conversion with a sub-cent fraction:
        1.99 USD * 60.5 = 120.395 DOP -> 120.40 (currency rounding in _convert)
        -> '12040' minor units (DOWN rounding of to_minor_currency_units acts on
        the already-rounded DOP amount). """
        if self.env.company.currency_id != self.currency_usd:
            self.skipTest("company currency is not USD")
        self._set_dop_rate(60.5)
        tx = self._create_transaction(
            flow='redirect', currency_id=self.currency_usd.id, amount=1.99,
            reference='TX-USD-002',
        )
        rendering_values = tx._get_specific_rendering_values(None)
        self.assertEqual(rendering_values['Amount'], '12040')

    def test_rendering_values_convert_third_currency(self):
        """ Test that any third currency is accepted and converted through the
        configured rates: 10 EUR * (60.5 DOP / 0.9 EUR) = 672.22 DOP. """
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_euro.id,
            'rate': 0.9,
            'name': fields.Date.context_today(self.env.user),
            'company_id': self.env.company.id,
        })
        self._set_dop_rate(60.5)
        tx = self._create_transaction(
            flow='redirect', currency_id=self.currency_euro.id, reference='TX-EUR-001'
        )
        rendering_values = tx._get_specific_rendering_values(None)
        self.assertEqual(rendering_values['Amount'], '67222')  # 605 / 0.9 = 672.222…
        self.assertEqual(rendering_values['CurrencyCode'], '$')

    def test_rendering_values_without_dop_rate_raises(self):
        """ Test that a non-DOP transaction with no usable DOP rate fails loudly
        instead of sending a suspicious amount to AZUL. """
        currency_x = self.env['res.currency'].create({'name': 'XZY', 'symbol': 'X'})
        # Remove any (demo) rate so that neither currency has a configured rate.
        self.env['res.currency.rate'].search([
            ('currency_id', 'in', (self.currency_dop.id, currency_x.id)),
        ]).unlink()
        tx = self._create_transaction(
            flow='redirect', currency_id=currency_x.id, reference='TX-NORATE-001'
        )
        with self.assertRaises(ValidationError):
            tx._get_specific_rendering_values(None)
        self.assertFalse(tx.azul_amount_sent)  # Nothing was sent nor persisted.

    def test_rendering_values_multicompany_uses_tx_company_rate(self):
        """ Test that the conversion uses the rate of the transaction company,
        not the current company (multi-company). """
        if self.env.company.currency_id != self.currency_usd:
            self.skipTest("company currency is not USD")
        company_b = self.env['res.company'].create({
            'name': "Company B", 'currency_id': self.currency_usd.id,
        })
        self._set_dop_rate(60.5)  # Main company rate.
        self._set_dop_rate(55.0, company=company_b)  # Company B rate.
        provider_b = self._prepare_provider('azul', company=company_b, update_values={
            'azul_merchant_id': '39038540035',
            'azul_merchant_name': 'Test Shop B',
            'azul_merchant_type': 'ECommerce',
            'azul_currency_code': '$',
            'azul_auth_key': 'dummy_azul_auth_key_for_tests',
        })
        tx = self._create_transaction(
            flow='redirect', provider_id=provider_b.id,
            currency_id=self.currency_usd.id, reference='TX-MC-001',
        )
        rendering_values = tx._get_specific_rendering_values(None)
        self.assertEqual(rendering_values['Amount'], '55000')  # 10.00 * 55.0, not 60.5.

    def test_get_tx_from_notification_data_returns_tx(self):
        """ Test that the transaction is found from the OrderNumber. """
        tx = self._create_transaction(flow='redirect')
        found_tx = self.env['payment.transaction']._get_tx_from_notification_data(
            'azul', {'OrderNumber': tx.reference}
        )
        self.assertEqual(found_tx, tx)

    def test_get_tx_from_notification_data_missing_order_number(self):
        """ Test that a notification without OrderNumber is rejected. """
        self._create_transaction(flow='redirect')
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._get_tx_from_notification_data('azul', {})

    def test_get_tx_from_notification_data_unknown_reference(self):
        """ Test that a notification matching no transaction is rejected. """
        self._create_transaction(flow='redirect')
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._get_tx_from_notification_data(
                'azul', {'OrderNumber': 'unknown-reference'}
            )

    def test_processing_approved_notification_sets_done(self):
        """ Test that an IsoCode 00 notification confirms the transaction and
        persists the vital AZUL data. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)  # Persist the amount sent.
        notification_data = self._azul_notification_data(tx)

        tx._handle_notification_data('azul', notification_data)

        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, '45678')
        self.assertEqual(tx.azul_order_id, '45678')
        self.assertEqual(tx.azul_authorization_code, 'OK1234')
        self.assertEqual(tx.azul_rrn, '20260704999999')
        self.assertEqual(tx.azul_iso_code, '00')
        self.assertEqual(tx.azul_response_message, 'APROBADA')
        self.assertEqual(tx.azul_date_time, '20260704120000')

    def test_processing_declined_notification_sets_error(self):
        """ Test that any IsoCode other than 00 never confirms the transaction
        (criterion 5). """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        notification_data = self._azul_notification_data(tx, iso_code='05')

        tx._handle_notification_data('azul', notification_data)

        self.assertEqual(tx.state, 'error')
        self.assertIn('05', tx.state_message)
        self.assertNotEqual(tx.state, 'done')

    @mute_logger('odoo.addons.azul_webpages.models.payment_transaction')
    def test_processing_amount_mismatch_sets_error(self):
        """ Test that a returned Amount different from the sent one is an error,
        never a confirmation. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)  # Sends Amount=1000.
        notification_data = self._azul_notification_data(tx, Amount='999999')

        tx._handle_notification_data('azul', notification_data)

        self.assertEqual(tx.state, 'error')
        self.assertNotEqual(tx.state, 'done')

    def test_duplicate_notification_is_idempotent(self):
        """ Test that a duplicated return does not re-process the transaction. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        notification_data = self._azul_notification_data(tx)

        tx._handle_notification_data('azul', notification_data)
        self.assertEqual(tx.state, 'done')
        tx._handle_notification_data('azul', notification_data)  # Must not raise.
        self.assertEqual(tx.state, 'done')

    def test_declined_after_done_does_not_downgrade(self):
        """ Test that an out-of-order declined notification cannot downgrade a
        confirmed transaction. """
        tx = self._create_transaction(flow='redirect')
        tx._get_specific_rendering_values(None)
        tx._handle_notification_data('azul', self._azul_notification_data(tx))
        self.assertEqual(tx.state, 'done')

        tx._handle_notification_data('azul', self._azul_notification_data(tx, iso_code='05'))
        self.assertEqual(tx.state, 'done')

    def test_cancel_marker_sets_canceled(self):
        """ Test that the cancellation marker injected by the controller cancels
        the transaction. """
        tx = self._create_transaction(flow='redirect')
        tx._handle_notification_data(
            'azul', {'OrderNumber': tx.reference, 'azul_cancel': True}
        )
        self.assertEqual(tx.state, 'cancel')

    def test_full_flow_with_odoo_style_reference(self):
        """ Test the render + return round trip with a typical Odoo reference
        containing hyphens ('S00042-1') in OrderNumber and both hashes. """
        tx = self._create_transaction(flow='redirect', reference='S00042-1')
        rendering_values = tx._get_specific_rendering_values(None)
        self.assertEqual(rendering_values['OrderNumber'], 'S00042-1')

        notification_data = self._azul_notification_data(tx)
        self.assertEqual(notification_data['OrderNumber'], 'S00042-1')
        tx._handle_notification_data('azul', notification_data)
        self.assertEqual(tx.state, 'done')
