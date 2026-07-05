/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import PaymentForm from "@payment/js/payment_form";

patch(PaymentForm.prototype, {

    /**
     * Override of `payment` to redirect AZUL token payments.
     *
     * AZUL has no server-to-server API, so paying with a saved card still
     * redirects to the Payment Page (where AZUL asks only for the CVV). The
     * server renders the redirect form for token transactions too, so it is
     * submitted here instead of navigating straight to the status page.
     *
     * @override
     */
    _processTokenFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode === 'azul' && processingValues.redirect_form_html) {
            this._processRedirectFlow(
                providerCode, paymentOptionId, paymentMethodCode, processingValues
            );
            return;
        }
        return super._processTokenFlow(...arguments);
    },
});
