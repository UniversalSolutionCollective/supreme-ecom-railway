# Supreme Store

A Flask storefront for dropshipping. Buyers can build a cart and check whether
its products can ship to their selected country. This build doesn't collect
payments, create orders, send anything to suppliers, or take delivery addresses.

## Local verification

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
gunicorn --bind 127.0.0.1:8080 app:app
```

Open http://127.0.0.1:8080/. `GET /health` reports readiness. To load a
local sample catalog instead of the empty default, set `CATALOG_PATH` to
its absolute file path before starting Gunicorn.

## Adding a verified product

`catalog.json` starts empty. Each entry must provide:

- `sku`: Unique uppercase product identifier (letters, digits, underscores or hyphens).
- `name`: Approved product name.
- `price_cents`: Selling price as an integer in the currency's minor units
  (for example, 9999 means 99.99). Supported currencies: USD, NGN, EUR, GBP, CAD, AUD.
- `currency`: One supported currency; mixed-currency carts are not quoted.
- `shipping_countries`: Explicit, supplier-confirmed ISO 3166-1 alpha-2 country codes
  for this SKU. List a country only if the supplier's coverage supports the country-level
  claim. Verify regional restrictions, stock and postal-code availability before taking payment.
- Optional `image_url`: An HTTPS URL for an image you have the right to use.

Restart after changing the catalog. The server uses the configured product price,
never a client-supplied amount. Cart checks show product subtotal only: shipping,
tax and duties are not calculated or shown as free. Never commit supplier credentials,
payment keys, customer data, a database dump or a virtual environment.

## Launch checklist: one product, one market

1. Confirm supplier stock and shipping coverage, landed cost, delivery times,
   returns process and product-use rights. Approve the retail price and margin.
2. Configure an approved business payment provider. For a one-product launch,
   a hosted physical-product page can collect a verified destination, delivery
   charge and payment in one place. Test that the page restricts unsupported
   destinations and caps order quantities to stock. A generic pay link is not
   enough for shipping.
3. Confirm customer-facing delivery and return information. Test an order in the
   provider's test mode, then confirm the intended fulfillment process. Send
   orders to suppliers only after verifying payment and availability.
4. After approval, connect the intended GitHub branch to a Railway staging service.
   The root Dockerfile starts Gunicorn on Railway's injected `PORT`. Set the
   Healthcheck Path to `/health`. Test the exact deployment and the customer journey
   before enabling live checkout or sharing a purchase link.

[Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles) ·
[Railway healthchecks](https://docs.railway.com/deployments/healthchecks)

## Project history

Rebuilt from the Flask storefront in
[supreme-store](https://github.com/UniversalSolutionCollective/supreme-store/tree/9e42cdea6a88f39d3970c81e5936a3628ac58e57).
The old demo listing, wallet text, bundled virtual environment and seller redirect
are not included.
