"""Read-only Supreme Store catalog. Purchases happen on the linked seller site."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template

ROOT = Path(__file__).resolve().parent


def https_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Invalid catalog URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Catalog URLs must use HTTPS without credentials")
    return value


def load_catalog(path):
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("The product catalog must be a JSON array")
    products = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each product must be an object")
        name = item.get("name")
        cents = item.get("price_cents")
        currency = item.get("currency")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("Invalid product name")
        if type(cents) is not int or not 0 <= cents <= 100_000_000:
            raise ValueError("Invalid price in cents")
        if currency not in ("USD", "NGN"):
            raise ValueError("Currency must be USD or NGN")
        image = item.get("image_url")
        products.append({
            "name": name.strip(),
            "price": f"{currency} {cents // 100:,}.{cents % 100:02d}",
            "checkout": https_url(item.get("checkout_url")),
            "image": https_url(image) if image is not None else None,
        })
    return products


def create_app(catalog_path=None):
    app = Flask(__name__, static_url_path="/assets")
    app.config["TEMPLATES_AUTO_RELOAD"] = False
    catalog_path = Path(catalog_path or os.environ.get("CATALOG_PATH") or ROOT / "catalog.json")
    products = load_catalog(catalog_path)

    @app.get("/")
    def home():
        return render_template("index.html", products=products)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src https:; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        return response

    return app


app = create_app()
