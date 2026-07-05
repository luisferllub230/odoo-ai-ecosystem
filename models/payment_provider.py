# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac

from odoo import fields, models

from odoo.addons.azul_webpages import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('azul', "Azul")], ondelete={'azul': 'set default'}
    )
    azul_merchant_id = fields.Char(
        string="Azul Merchant ID",
        help="The merchant affiliation number (MID) assigned by AZUL.",
        required_if_provider='azul',
    )
    azul_merchant_name = fields.Char(
        string="Azul Merchant Name",
        help="The merchant name displayed on the AZUL Payment Page.",
        required_if_provider='azul',
    )
    azul_merchant_type = fields.Char(
        string="Azul Merchant Type",
        help="Informative merchant type sent to AZUL (e.g. ECommerce).",
        default="ECommerce",
        required_if_provider='azul',
    )
    azul_currency_code = fields.Char(
        string="Azul Currency Code",
        help="The exact CurrencyCode value delivered by AZUL with the credentials. "
             "Each MID transacts in a single currency (DOP); the PDF example uses '$'.",
        default="$",
        required_if_provider='azul',
    )
    azul_auth_key = fields.Char(
        string="Azul Auth Key",
        help="The authentication key delivered by AZUL at affiliation time. "
             "It never travels in the POST; it is only used to compute the AuthHash.",
        required_if_provider='azul',
        groups='base.group_system',
    )
    azul_use_alternate_url = fields.Boolean(
        string="Use Azul Alternate Site",
        help="Manual contingency switch: send payments to the alternate production "
             "site (contpagos.azul.com.do) when the main site is down.",
        default=False,
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable tokenization for AZUL.

        AZUL supports tokenization through its DataVault: the card entered on the
        Payment Page can be stored by AZUL, which returns a `DataVaultToken` used
        for later payments (the customer only re-enters the CVV on the Page).
        """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'azul').update({
            'support_tokenization': True,
        })

    # === BUSINESS METHODS === #

    # NOTE on supported currencies: `_get_supported_currencies()` is intentionally
    # NOT overridden. Per project decision, the provider accepts transactions in
    # any currency; the amount is always converted to DOP (the single currency of
    # the AZUL MID) before being sent to the Payment Page. See
    # `payment.transaction._azul_get_dop_amounts()`.

    def _azul_get_api_url(self):
        """ Return the URL of the AZUL Payment Page for this provider's state.

        See PDF p.13: test URL, production main site and production alternate
        (contingency) site.

        :return: The AZUL Payment Page URL.
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'test':
            return const.PAYMENT_PAGE_URLS['test']
        if self.azul_use_alternate_url:
            return const.PAYMENT_PAGE_URLS['prod_alternate']
        return const.PAYMENT_PAGE_URLS['prod']

    def _azul_calculate_hash(self, values):
        """ Compute the AZUL AuthHash for the given ordered field values.

        Algorithm (PDF p.65-66): concatenate the values in the documented order,
        append the AuthKey at the end of the string (the key is used both at the
        end of the string and as the HMAC key), and compute an HMAC SHA-512 over
        the message, output as lowercase hex.

        Encoding, per the PHP example on p.66: the MESSAGE is encoded in UTF-16LE
        (`mb_convert_encoding($str, 'UTF-16LE', ...)`), but the HMAC KEY is passed
        raw (`hash_hmac('sha512', $str, $authKey)` uses the key's own bytes, not a
        UTF-16LE re-encoding). Encoding the key in UTF-16LE produces a hash AZUL
        rejects with `INVALID_AUTH:AuthHash`.

        :param list values: The ordered field values (strings) to hash.
        :return: The lowercase hexadecimal HMAC SHA-512 digest.
        :rtype: str
        """
        self.ensure_one()
        auth_key = self.sudo().azul_auth_key or ''
        message = ''.join(str(value) if value is not None else '' for value in values) + auth_key
        return hmac.new(
            auth_key.encode('utf-8'), message.encode('utf-16-le'), hashlib.sha512
        ).hexdigest()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'azul':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
