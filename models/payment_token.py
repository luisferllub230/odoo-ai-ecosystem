# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    azul_datavault_expiration = fields.Char(
        string="Azul DataVault Expiration",
        help="Expiration of the AZUL DataVault token, in AAAAMM format, as "
             "returned by the Payment Page.",
        readonly=True,
    )
