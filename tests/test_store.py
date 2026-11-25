import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import create_app


class StoreTests(unittest.TestCase):
    def build(self, products):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(products), encoding="utf-8")
            return create_app(path).test_client()

    def product(self, **overrides):
        return {"name": "Ring", "price_cents": 9999, "currency": "USD",
                "checkout_url": "https://seller.example/ring", **overrides}

    def test_empty_store_and_styles(self):
        client = self.build([])
        self.assertIn(b"No products are listed", client.get("/").data)
        self.assertEqual(client.get("/assets/store.css", buffered=True).status_code, 200)

    def test_health(self):
        self.assertEqual(self.build([]).get("/health").json, {"status": "ok"})

    def test_catalog_price_and_external_checkout(self):
        response = self.build([self.product()]).get("/")
        self.assertIn(b"USD 99.99", response.data)
        self.assertIn(b'https://seller.example/ring', response.data)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_product_name_escaped(self):
        response = self.build([self.product(name="<script>")]).get("/")
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>", response.data)

    def test_reject_unsafe_or_invalid_catalog(self):
        cases = [
            {"checkout_url": "http://seller.example/ring"},
            {"checkout_url": "javascript:alert(1)"},
            {"checkout_url": "https://user:pass@seller.example/"},
            {"image_url": "not an image URL"},
            {"price_cents": True},
            {"price_cents": -1},
        ]
        for override in cases:
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.build([self.product(**override)])


if __name__ == "__main__":
    unittest.main()
