===================================
Payment Provider: AZUL Payment Page
===================================

This module integrates the **AZUL Payment Page** (Banco Popular Dominicano's
e-commerce gateway for the Dominican Republic) with the Odoo 18 ``payment``
framework, using the browser redirect flow documented in the public
*E-Commerce AZUL — Página de Pagos* manual (2023-08 edition, referenced below
as *PDF p.N*).

Payment flow
============

1. The customer selects *Azul* (card) at checkout, in the portal or from a
   payment link. Odoo renders an auto-submitted HTML form (the standard
   ``online_redirect`` flow of the payment framework).
2. The customer's **browser** POSTs the sale form to the AZUL Payment Page
   (PDF p.13) with the transaction detail and an ``AuthHash`` (HMAC SHA-512).
3. The customer pays on AZUL's site. AZUL redirects the browser back to Odoo:

   - ``ApprovedUrl`` / ``DeclinedUrl`` — ``/payment/azul/return/approved`` or
     ``/payment/azul/return/declined``, with the response in the querystring,
     signed with a response ``AuthHash`` (PDF p.16).
   - ``CancelUrl`` — ``/payment/azul/return/cancel``, **without** parameters
     (PDF p.15); the module embeds its own ``reference`` and ``access_token``
     in the URL to correlate the transaction.

4. Odoo verifies, in this order, before touching any state:

   a. its own ``access_token`` embedded in the return URL;
   b. the **response hash** (strict: missing or invalid hash → HTTP 403,
      state untouched).

5. Only a hash-verified ``IsoCode = 00`` confirms the transaction (PDF p.69).
   Any other code sets the transaction in error with the ``IsoCode``,
   ``ResponseMessage`` and ``ErrorDescription``. The route (approved vs
   declined) never decides the state.
6. A ``done`` transaction goes through the standard post-processing
   (``/payment/status`` + cron): the invoice is reconciled by the framework.

There is **no server-to-server confirmation**: the Payment Page product does
not document any webhook or query endpoint. If the customer never returns to
Odoo after paying, the transaction stays pending; reconcile manually with the
AZUL portal using the vital data stored on the transaction (Azul Order ID,
authorization code, RRN, date/time).

Currency handling (project decision)
====================================

The AZUL MID transacts **only in Dominican peso (DOP)** — one MID, one
currency (PDF p.14). This module therefore:

- accepts transactions in **any** currency (``_get_supported_currencies`` is
  not restricted);
- **converts** the amount to DOP with the latest rate (transaction company,
  current date) before sending it to AZUL;
- always sends the ``CurrencyCode`` configured for the MID (``$`` per the PDF
  example);
- documents the conversion on the transaction (*Azul Currency Conversion*
  field), together with the exact ``Amount``/``ITBIS`` sent.

Make sure the DOP currency is active and has an up-to-date rate when selling
in other currencies.

ITBIS
=====

``ITBIS`` is the sum of the taxes of the sale orders / invoices linked to the
transaction, converted to DOP like the amount, in cents without separator
(same format as ``Amount``, PDF p.14). When no tax breakdown is available (no
linked document, or a breakdown larger than the paid amount, e.g. a partial
payment link) the module sends ``000`` (= 0.00, tax-exempt format).

AuthHash algorithm
==================

HMAC **SHA-512**, lowercase hexadecimal output (PDF p.65-66):

- **Request** string: ``MerchantId + MerchantName + MerchantType +
  CurrencyCode + OrderNumber + Amount + ITBIS + ApprovedUrl + DeclinedUrl +
  CancelUrl + UseCustomField1 + CustomField1Label + CustomField1Value +
  UseCustomField2 + CustomField2Label + CustomField2Value + AuthKey``
- **Response** string: ``OrderNumber + Amount + AuthorizationCode + DateTime +
  ResponseCode + IsoCode + ResponseMessage + ErrorDescription + RRN +
  AuthKey``
- The ``AuthKey`` is used **twice**, as in both PDF examples: appended at the
  end of the string *and* as the HMAC key.
- **Encoding (critical):** the *message* is encoded in **UTF-16LE** ("Unicode"
  in the C#/PHP examples), but the *HMAC key* is passed as **raw bytes** (the
  key's own UTF-8/ASCII bytes), following the PHP example on p.66
  (``mb_convert_encoding($str, 'UTF-16LE', ...)`` for the message,
  ``hash_hmac('sha512', $str, $authKey)`` with the key untouched). Encoding the
  key in UTF-16LE as well produces a hash AZUL rejects with
  ``INVALID_AUTH:AuthHash``.
- The ``AuthKey`` never travels in the POST and is never logged.

Tokenization (DataVault)
========================

AZUL can store the card in its **DataVault** and return a token for later
payments (PDF p.35-38). The provider enables Odoo tokenization
(``support_tokenization``):

- **Saving a card:** when the customer ticks *Save my payment details* at
  checkout, the sale form is sent with ``SaveToDataVault=1``. On an approved
  return AZUL adds ``DataVaultToken`` / ``DataVaultExpiration`` /
  ``DataVaultBrand`` to the querystring; the module creates a ``payment.token``
  whose ``provider_ref`` is the ``DataVaultToken``. AZUL only tokenizes an
  **approved** card (PDF p.35), so a declined payment never creates a token.
- **Paying with a saved card:** the transaction is sent with the stored
  ``DataVaultToken``; AZUL pre-fills the card and asks only for the CVV. Because
  AZUL has no server-to-server API, a token payment **still redirects** to the
  Payment Page (a small ``payment_form.js`` patch submits the redirect form for
  the token flow instead of processing it silently).
- ``SaveToDataVault`` and ``DataVaultToken`` do **not** participate in the
  ``AuthHash`` (PDF p.16/p.30, HASH column = *No*), so the request/response
  hashed field lists are unchanged.
- Enable tokenization per provider with *Allow Saving Payment Methods*.

Configuration
=============

#. Go to *Settings → Website / Accounting → Payment Providers → Azul*.
#. Fill in the credentials delivered by AZUL (system administrators only):
   *Merchant ID*, *Merchant Name*, *Merchant Type* (``ECommerce``),
   *Currency Code* (``$``) and *Auth Key*.
#. Set the state: *Test Mode* posts to ``https://pruebas.azul.com.do``,
   *Enabled* posts to production. The *Use Alternate Site* checkbox is a
   manual contingency switch to ``contpagos.azul.com.do`` (PDF p.13; automatic
   failover of a browser POST is not possible).
#. Publish the provider.

Notes:

- AZUL validates the return URLs against the hostname registered with them
  (``INVALID_BASEDOMAIN``, PDF p.75): register your Odoo domain with AZUL.
- The AZUL test environment blocks IPs outside the Dominican Republic unless
  whitelisted (PDF p.77).

Sandbox test data
=================

Demo data configures the provider in test mode with the AZUL test environment
credentials provided by the project owner (task 5). They are **not** published
by AZUL in the Payment Page PDF (the PDF example uses MerchantId
``99999999999``). Test mode only — **DO NOT use in production**:

- MerchantId: ``39038540035``
- AuthKey: ``asdhakjshdkjasdasmndajksdkjaskldga8odya9d8yoasyd98asdyaisdhoaisyd0a8sydoashd8oasydoiahdpiashd09ayusidhaos8dy0a8dya08syd0a8ssdsax``

Test cards (AZUL test environment only; expiration 12/2026). The flow is pure
redirect — the cards are typed on AZUL's page, never stored in Odoo:

================= ==================== =====
Brand             Number               CVV
================= ==================== =====
VISA              4035874000424977     977
MasterCard        5426064000424979     979
VISA              4012000033330026     123
MasterCard        5424180279791732     732
DISCOVER          6011000999099818     818
VISA              4260550061845872     872
================= ==================== =====

Troubleshooting
===============

- ``IsoCode`` ``00`` is the **only** approval code; ``03/04/05/07/12/13/14…``
  are issuer declines (PDF p.69+). The full received response is stored on the
  transaction and in the server log.
- ``VALIDATION_ERROR:FieldName`` — a request field does not satisfy AZUL's
  validation; check the rendered form values.
- ``INVALID_BASEDOMAIN:ApproveURL`` — the return URL hostname is not the one
  registered with AZUL.
- HTTP 403 on return — response hash or access token verification failed; the
  transaction state is never modified in that case.
- Card data must never be logged (PDF p.67); this module never sees it.

Technical notes
===============

- Provider code: ``azul``; flows: ``online_redirect`` and ``online_token``
  (the token flow also redirects, see *Tokenization*). Adds one field to
  ``payment.token`` (``azul_datavault_expiration``) and a small frontend JS
  patch.
- Out of scope: HOLD/POST/VOID, explicit 3-D Secure (handled inside AZUL's
  page), DCC, installments, refunds from Odoo.
- Tests: ``odoo -d <db> -i azul_webpages --test-enabled --stop-after-init``.
