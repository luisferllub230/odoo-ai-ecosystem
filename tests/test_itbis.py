# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from unittest import SkipTest

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.azul_webpages.tests.common import AzulCommon


@tagged('post_install', '-at_install')
class TestAzulItbis(AzulCommon):
    """ Coverage of `_azul_get_itbis_minor_units` against real linked documents.

    These tests need the `sale` module (the `sale_order_ids` field on
    `payment.transaction`); they are skipped when it is not installed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'sale_order_ids' not in cls.env['payment.transaction']._fields:
            raise SkipTest("sale is not installed; linked-document ITBIS is not testable")

        cls.tax_18 = cls.env['account.tax'].create({
            'name': "ITBIS 18%",
            'amount': 18.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        cls.product = cls.env['product.product'].create({
            'name': "Azul Test Product",
            'list_price': 100.0,
        })
        cls.pricelist_dop = cls.env['product.pricelist'].create({
            'name': "DOP Pricelist", 'currency_id': cls.currency_dop.id,
        })
        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': "USD Pricelist", 'currency_id': cls.currency_usd.id,
        })

    def _create_order(self, pricelist, price_unit=100.0):
        """ Create a sale order of one line at `price_unit` + 18% tax. """
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': pricelist.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': price_unit,
                'tax_id': [Command.set(self.tax_18.ids)],
            })],
        })

    def _create_linked_tx(self, order, **values):
        return self._create_transaction(
            flow='redirect', sale_order_ids=[Command.set(order.ids)], **values
        )

    def test_itbis_from_dop_sale_order(self):
        """ Test that ITBIS is the tax of the linked order in DOP cents:
        100.00 + 18% -> ITBIS '1800', Amount '11800'. """
        order = self._create_order(self.pricelist_dop)
        self.assertEqual(order.amount_tax, 18.0)
        tx = self._create_linked_tx(order, amount=order.amount_total)

        rendering_values = tx._get_specific_rendering_values(None)

        self.assertEqual(rendering_values['Amount'], '11800')
        self.assertEqual(rendering_values['ITBIS'], '1800')
        self.assertEqual(tx.azul_itbis_sent, '1800')

    def test_itbis_converted_from_usd_order(self):
        """ Test that a USD order tax is converted to DOP like the amount:
        18.00 USD * 60.5 -> ITBIS '108900'; 118.00 USD * 60.5 -> Amount '713900'. """
        if self.env.company.currency_id != self.currency_usd:
            self.skipTest("company currency is not USD")
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_dop.id,
            'rate': 60.5,
            'name': fields.Date.context_today(self.env.user),
            'company_id': self.env.company.id,
        })
        order = self._create_order(self.pricelist_usd)
        tx = self._create_linked_tx(
            order, amount=order.amount_total, currency_id=self.currency_usd.id
        )

        rendering_values = tx._get_specific_rendering_values(None)

        self.assertEqual(rendering_values['Amount'], '713900')  # 118.00 * 60.5
        self.assertEqual(rendering_values['ITBIS'], '108900')  # 18.00 * 60.5

    def test_itbis_exceeding_amount_falls_back_to_zero(self):
        """ Test that an ITBIS larger than the paid amount (e.g. partial payment
        link) falls back to '000': no coherent breakdown is available. """
        order = self._create_order(self.pricelist_dop)  # Tax 18.00 DOP.
        tx = self._create_linked_tx(order, amount=10.0)  # Partial: 10.00 DOP.

        rendering_values = tx._get_specific_rendering_values(None)

        self.assertEqual(rendering_values['Amount'], '1000')
        self.assertEqual(rendering_values['ITBIS'], '000')

    def test_itbis_equal_to_amount_is_kept(self):
        """ Test the boundary: an ITBIS exactly equal to the paid amount is kept
        (the fallback only triggers when ITBIS exceeds the amount). """
        order = self._create_order(self.pricelist_dop)  # Tax 18.00 DOP.
        tx = self._create_linked_tx(order, amount=18.0)

        rendering_values = tx._get_specific_rendering_values(None)

        self.assertEqual(rendering_values['Amount'], '1800')
        self.assertEqual(rendering_values['ITBIS'], '1800')
