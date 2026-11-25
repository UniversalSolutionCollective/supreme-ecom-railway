"""Supreme Store catalog and server-validated dropshipping cart preview."""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent
SKU = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,39}")
COUNTRY = re.compile(r"[A-Z]{2}")
MAX_LINES, MAX_UNITS = 25, 20


def https_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Invalid catalog URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Catalog URLs must use HTTPS without credentials")
    return value


def is_minor(value):
    return type(value) is int and 0 <= value <= 100_000_000


def format_price(amount, currency):
    return f"{currency} {amount // 100:,}.{amount % 100:02d}"


def load_catalog(path):
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("The product catalog must be a JSON array")
    products = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each product must be an object")
        sku, name = item.get("sku"), item.get("name")
        amount, currency = item.get("price_cents"), item.get("currency")
        countries = item.get("shipping_countries")
        if not isinstance(sku, str) or not SKU.fullmatch(sku) or sku in products:
            raise ValueError("Each product needs a unique SKU")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("Invalid product name")
        if not is_minor(amount) or currency not in ("USD", "NGN", "EUR", "GBP", "CAD", "AUD"):
            raise ValueError("Invalid price or unsupported two-decimal currency")
        if (not isinstance(countries, list) or not countries
                or any(not isinstance(code, str) or not COUNTRY.fullmatch(code) for code in countries)
                or len(countries) != len(set(countries))):
            raise ValueError("Each product needs a distinct list of supplier-confirmed country codes")
        image = item.get("image_url")
        products[sku] = {
            "sku": sku, "name": name.strip(), "amount": amount, "currency": currency,
            "price": format_price(amount, currency), "countries": frozenset(countries),
            "image": https_url(image) if image is not None else None,
        }
    return products


def create_app(catalog_path=None):
    app = Flask(__name__, static_url_path="/assets")
    app.config.update(TEMPLATES_AUTO_RELOAD=False, MAX_CONTENT_LENGTH=8192)
    catalog_path = Path(catalog_path or os.environ.get("CATALOG_PATH") or ROOT / "catalog.json")
    products = load_catalog(catalog_path)
    destinations = sorted({code for product in products.values() for code in product["countries"]})

    @app.get("/")
    def home():
        return render_template("index.html", products=products.values(), destinations=destinations)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/cart/preview")
    def preview():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Send a JSON cart."), 400
        country, items = data.get("country"), data.get("items")
        if not isinstance(country, str) or not COUNTRY.fullmatch(country):
            return jsonify(error="Select a delivery country."), 400
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_LINES:
            return jsonify(error="Your cart must contain between 1 and 25 products."), 400
        lines, seen, currencies, unavailable = [], set(), set(), []
        for item in items:
            if not isinstance(item, dict):
                return jsonify(error="Invalid cart item."), 400
            sku, quantity = item.get("sku"), item.get("quantity")
            if (not isinstance(sku, str) or not SKU.fullmatch(sku) or sku in seen
                    or type(quantity) is not int or not 1 <= quantity <= MAX_UNITS):
                return jsonify(error="Invalid product or quantity in cart."), 400
            seen.add(sku)
            product = products.get(sku)
            if product is None:
                return jsonify(error="A product is no longer available. Update your cart."), 400
            if country not in product["countries"]:
                unavailable.append(product["name"])
            currencies.add(product["currency"])
            lines.append(product["amount"] * quantity)

        if unavailable:
            return jsonify(error="Some products cannot ship to the selected country.",
                           unavailable=unavailable, checkout_enabled=False), 422
        if len(currencies) != 1:
            return jsonify(error="Items priced in different currencies need separate carts.",
                           checkout_enabled=False), 422
        currency = currencies.pop()
        return jsonify(
            country=country, currency=currency, subtotal_cents=sum(lines),
            subtotal=format_price(sum(lines), currency), shipping_status="eligible",
            shipping_fee_cents=None, taxes_and_duties_cents=None, checkout_enabled=False,
        )

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="This cart request is too large."), 413

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "img-src https:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()
