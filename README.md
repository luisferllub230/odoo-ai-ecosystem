# azul_webpages

Odoo 18 payment provider for the **AZUL Payment Page** (Dominican Republic),
browser redirect flow.

- Provider code `azul`, `online_redirect` flow, card payment method.
- HMAC SHA-512 (`AuthHash`) on request and strict verification on return —
  the redirect querystring is the only confirmation channel (no webhook).
- Amounts always sent in **DOP**: non-DOP transactions are converted with the
  latest rate and the conversion is documented on the transaction.
- Only `IsoCode = 00` confirms a payment; duplicated or out-of-order returns
  never re-process a transaction.

See `doc/index.rst` for the full flow, hash algorithm, configuration,
sandbox credentials and test cards.

License: LGPL-3. Author: Luis Fernández.
