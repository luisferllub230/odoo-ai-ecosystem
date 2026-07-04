# Part of azul_webpages. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import hmac as hmac_tool

from odoo.addons.payment import utils as payment_utils
from odoo.addons.azul_webpages import const
from odoo.addons.azul_webpages.controllers.main import AzulController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # Vital data returned by AZUL, kept verbatim so a human can locate and
    # validate the payment on the AZUL portal and so the response hash remains
    # reproducible.
    azul_order_id = fields.Char(string="Azul Order ID", readonly=True)
    azul_authorization_code = fields.Char(string="Azul Authorization Code", readonly=True)
    azul_rrn = fields.Char(string="Azul RRN", readonly=True)
    azul_iso_code = fields.Char(string="Azul ISO Code", readonly=True)
    azul_response_message = fields.Char(string="Azul Response Message", readonly=True)
    azul_date_time = fields.Char(
        string="Azul Date Time",
        help="The DateTime value returned by AZUL, kept verbatim to reproduce the "
             "response hash and to search the transaction on the AZUL portal.",
        readonly=True,
    )
    # Values sent to AZUL, in DOP minor units, kept to check the coherence of
    # the returned Amount and to document the currency conversion (the AZUL MID
    # transacts only in DOP).
    azul_amount_sent = fields.Char(
        string="Azul Amount Sent",
        help="The Amount value sent to AZUL, in DOP cents without separator.",
        readonly=True,
    )
    azul_itbis_sent = fields.Char(
        string="Azul ITBIS Sent",
        help="The ITBIS value sent to AZUL, in DOP cents without separator.",
        readonly=True,
    )
    azul_conversion_details = fields.Char(
        string="Azul Currency Conversion",
        help="Details of the conversion of the transaction amount to DOP, when the "
             "transaction currency is not DOP.",
        readonly=True,
    )

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return AZUL-specific rendering values.

        The returned dict contains one entry per POST field of the AZUL Payment
        Page sale form, with the exact field names of the PDF (p.14), plus the
        `api_url` used as the form action.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'azul':
            return res

        provider = self.provider_id
        amount_minor, itbis_minor, conversion_details = self._azul_get_dop_amounts()
        amount_str = str(amount_minor)
        itbis_str = str(itbis_minor) if itbis_minor else '000'  # 000 = 0.00 (PDF p.14)

        # Build the return URLs with our own correlation parameters. AZUL
        # appends its response to the querystring of ApprovedUrl/DeclinedUrl but
        # calls CancelUrl without any parameter (PDF p.15), so the reference and
        # an access token of our own are embedded in all three URLs.
        base_url = provider.get_base_url()
        access_token = self._azul_generate_access_token()
        return_params = urls.url_encode({
            'reference': self.reference,
            'access_token': access_token,
        })
        approved_url = f'{urls.url_join(base_url, AzulController._approved_url)}?{return_params}'
        declined_url = f'{urls.url_join(base_url, AzulController._declined_url)}?{return_params}'
        cancel_url = f'{urls.url_join(base_url, AzulController._cancel_url)}?{return_params}'

        rendering_values = {
            'MerchantId': provider.azul_merchant_id,
            'MerchantName': provider.azul_merchant_name,
            'MerchantType': provider.azul_merchant_type,
            'CurrencyCode': provider.azul_currency_code,
            'OrderNumber': self.reference,
            'Amount': amount_str,
            'ITBIS': itbis_str,
            'ApprovedUrl': approved_url,
            'DeclinedUrl': declined_url,
            'CancelUrl': cancel_url,
            'UseCustomField1': '0',
            'CustomField1Label': '',
            'CustomField1Value': '',
            'UseCustomField2': '0',
            'CustomField2Label': '',
            'CustomField2Value': '',
            'Locale': 'EN' if (self.partner_lang or 'es').startswith('en') else 'ES',
        }
        rendering_values['AuthHash'] = provider._azul_calculate_hash(
            [rendering_values[field_name] for field_name in const.REQUEST_HASH_FIELDS]
        )
        rendering_values['api_url'] = provider._azul_get_api_url()

        # Document the values sent to AZUL on the transaction (amount coherence
        # check on return + traceability of the DOP conversion).
        self.write({
            'azul_amount_sent': amount_str,
            'azul_itbis_sent': itbis_str,
            'azul_conversion_details': conversion_details,
        })
        return rendering_values

    def _azul_get_dop_amounts(self):
        """ Return the transaction amount and ITBIS converted to DOP minor units.

        The AZUL MID transacts in a single currency (DOP). Per project decision,
        transactions in any other currency are converted to DOP with the latest
        rate (company and current date) before being sent to AZUL.

        The ITBIS is the sum of the taxes of the linked sale orders/invoices
        when they exist (converted to DOP the same way); 0 when no tax breakdown
        is available or when it is not coherent with the amount.

        Note: self.ensure_one()

        :return: A tuple (amount_minor, itbis_minor, conversion_details) where
                 the amounts are integers in DOP cents and conversion_details is
                 a human-readable string or False.
        :rtype: tuple(int, int, str|bool)
        """
        self.ensure_one()
        currency_dop = self.env.ref('base.DOP')
        company = self.company_id or self.provider_id.company_id
        conversion_date = fields.Date.context_today(self)

        conversion_details = False
        if self.currency_id == currency_dop:
            amount_dop = self.amount
        else:
            amount_dop = self.currency_id._convert(
                self.amount, currency_dop, company, conversion_date
            )
            conversion_details = (
                f"{self.amount:.2f} {self.currency_id.name} converted to "
                f"{amount_dop:.2f} DOP on {conversion_date} (latest rate of company "
                f"{company.name}) before sending to AZUL."
            )
        amount_minor = payment_utils.to_minor_currency_units(amount_dop, currency_dop)

        itbis_minor = self._azul_get_itbis_minor_units(currency_dop, company, conversion_date)
        if itbis_minor > amount_minor:  # No coherent tax breakdown for the paid amount.
            itbis_minor = 0
        return amount_minor, itbis_minor, conversion_details

    def _azul_get_itbis_minor_units(self, currency_dop, company, conversion_date):
        """ Return the ITBIS of the linked documents in DOP minor units.

        The fields `sale_order_ids` and `invoice_ids` only exist when the
        optional bridge modules (`sale`, `account_payment`) are installed, hence
        the guards on `self._fields`.

        :param recordset currency_dop: The DOP currency, as a `res.currency` record.
        :param recordset company: The company used for the conversion.
        :param date conversion_date: The date of the conversion rate.
        :return: The ITBIS in DOP cents, 0 when no tax breakdown is available.
        :rtype: int
        """
        self.ensure_one()
        documents = []
        if 'sale_order_ids' in self._fields and self.sale_order_ids:
            documents = [(order.currency_id, order.amount_tax) for order in self.sale_order_ids]
        elif 'invoice_ids' in self._fields and self.invoice_ids:
            documents = [(move.currency_id, move.amount_tax) for move in self.invoice_ids]
        if not documents:
            return 0

        itbis_dop = sum(
            doc_currency._convert(tax_amount, currency_dop, company, conversion_date)
            if doc_currency != currency_dop else tax_amount
            for doc_currency, tax_amount in documents
        )
        return payment_utils.to_minor_currency_units(itbis_dop, currency_dop)

    def _azul_generate_access_token(self):
        """ Generate the access token embedded in the AZUL return URLs.

        Equivalent to `payment.utils.generate_access_token(self.reference)` but
        usable outside of an HTTP request (the token is verified in the
        controller with `payment.utils.check_access_token`).

        :return: The access token.
        :rtype: str
        """
        self.ensure_one()
        return hmac_tool(self.env(su=True), 'generate_access_token', str(self.reference))

    # === BUSINESS METHODS - NOTIFICATION PROCESSING === #

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on AZUL data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'azul' or len(tx) == 1:
            return tx

        reference = notification_data.get('OrderNumber')
        if not reference:
            raise ValidationError("AZUL: " + _("Received data with missing OrderNumber."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'azul')])
        if not tx:
            raise ValidationError(
                "AZUL: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _azul_compute_response_hash(self, notification_data):
        """ Compute the expected AuthHash of an AZUL return querystring.

        The concatenation order is the one mandated by the PDF (p.65):
        OrderNumber + Amount + AuthorizationCode + DateTime + ResponseCode +
        IsoCode + ResponseMessage + ErrorDescription + RRN + AuthKey.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: The expected lowercase hexadecimal HMAC SHA-512 digest.
        :rtype: str
        """
        self.ensure_one()
        return self.provider_id._azul_calculate_hash(
            [notification_data.get(field_name, '') for field_name in const.RESPONSE_HASH_FIELDS]
        )

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on AZUL data.

        The response hash MUST have been verified by the caller (controller)
        before this method is reached; this method only maps the (authenticated)
        data onto the transaction state.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'azul':
            return

        # Cancellation return: AZUL calls CancelUrl without any parameter
        # (PDF p.15); the controller injects this marker after validating our
        # own access token.
        if notification_data.get('azul_cancel'):
            self._set_canceled(
                state_message=_("The customer canceled the payment on the AZUL Payment Page.")
            )
            return

        # Persist the vital data of the transaction (verbatim, criterion 6).
        self.write({
            'azul_order_id': notification_data.get('AzulOrderId'),
            'azul_authorization_code': notification_data.get('AuthorizationCode'),
            'azul_rrn': notification_data.get('RRN'),
            'azul_iso_code': notification_data.get('IsoCode'),
            'azul_response_message': notification_data.get('ResponseMessage'),
            'azul_date_time': notification_data.get('DateTime'),
        })
        if notification_data.get('AzulOrderId'):
            self.provider_reference = notification_data['AzulOrderId']

        # Amount coherence: the returned Amount must match the Amount sent.
        amount_sent = self.azul_amount_sent or str(self._azul_get_dop_amounts()[0])
        amount_received = str(notification_data.get('Amount', ''))
        if amount_received != amount_sent:
            _logger.warning(
                "AZUL returned a different amount (%s) than the one sent (%s) for "
                "transaction with reference %s.",
                amount_received, amount_sent, self.reference,
            )
            self._set_error(_(
                "AZUL: The returned amount (%(returned)s) does not match the amount sent "
                "(%(sent)s).", returned=amount_received, sent=amount_sent,
            ))
            return

        # State mapping: IsoCode '00' is the only approval code (PDF p.69).
        iso_code = notification_data.get('IsoCode')
        if iso_code == const.APPROVED_ISO_CODE:
            self._set_done()
        else:
            error_message = _(
                "AZUL: Payment declined or failed (IsoCode: %(iso_code)s; "
                "ResponseMessage: %(response_message)s; ErrorDescription: %(error_description)s).",
                iso_code=iso_code,
                response_message=notification_data.get('ResponseMessage', ''),
                error_description=notification_data.get('ErrorDescription', ''),
            )
            _logger.info(
                "Received AZUL notification with IsoCode %s for transaction with reference %s.",
                iso_code, self.reference,
            )
            self._set_error(error_message)
