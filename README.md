# Supreme Store
A Flask storefront that lists approved products and links to seller checkout pages. This app does not collect payments or customer data.

## Local verification
```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
gunicorn --bind 127.0.0.1:8080 app:app
```

Open http://127.0.0.1:8080/. `GET /health` reports readiness.

## Catalog
`catalog.json` is empty until products are approved. Each entry uses `name`, `price_cents` (integer minor units), `currency` (`USD` or `NGN`), `checkout_url` (verified HTTPS seller page) and optionally `image_url` (HTTPS). Restart after changing the catalog. To import products from an older deployment, first verify the products, prices, image rights and checkout destinations. Never commit secrets, customer data, a database dump, or a virtual environment.

## Railway
For an authorized release, connect the destination GitHub repo to a Railway staging service. The root Dockerfile starts Gunicorn on Railway's injected `PORT`. Set the service's Healthcheck Path to `/health`, then verify `/` and each approved seller link before any public launch. See [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles) and [Railway healthchecks](https://docs.railway.com/deployments/healthchecks).

## Project history
This Railway edition was rebuilt from the Flask storefront in [supreme-store](https://github.com/UniversalSolutionCollective/supreme-store/tree/9e42cdea6a88f39d3970c81e5936a3628ac58e57). The old demo listing, wallet text and bundled virtual environment are not included.
