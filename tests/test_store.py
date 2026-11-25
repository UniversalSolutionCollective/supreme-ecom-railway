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
        return {"sku": "RING-01", "name": "Test ring", "price_cents": 9999, "currency": "USD",
                "shipping_countries": ["US"], **overrides}

    def quote(self, client, country="US", lines=None):
        return client.post("/api/cart/preview", json={
            "country": country, "items": [{"sku": "RING-01", "quantity": 2}] if lines is None else lines
        })

    def test_empty_store_health_and_static_assets(self):
        client = self.build([])
        self.assertIn(b"No products are listed", client.get("/").data)
        self.assertEqual(client.get("/health").json, {"status": "ok"})
        for name in ("store.css", "cart.js"):
            response = client.get(f"/assets/{name}", buffered=True)
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_product_name_escaped_and_no_seller_checkout(self):
        response = self.build([self.product(name="<script>", checkout_url="https://seller.example")]).get("/")
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertIn(b"Online checkout is not open yet", response.data)
        self.assertNotIn(b"<script>", response.data)
        self.assertNotIn(b"seller.example", response.data)
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])

    def test_country_and_subtotal_are_calculated_server_side(self):
        response = self.quote(self.build([self.product()]), lines=[
            {"sku": "RING-01", "quantity": 2, "price_cents": 1}
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["subtotal_cents"], 19998)
        self.assertEqual(response.json["subtotal"], "USD 199.98")
        self.assertEqual(response.json["shipping_status"], "eligible")
        self.assertIsNone(response.json["shipping_fee_cents"])
        self.assertIsNone(response.json["taxes_and_duties_cents"])
        self.assertFalse(response.json["checkout_enabled"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_country_must_be_supported_for_every_item(self):
        client = self.build([self.product(), self.product(sku="RING-02", name="Test item two",
                                                          shipping_countries=["GB"])])
        response = self.quote(client, "US", [{"sku": "RING-01", "quantity": 1}, {"sku": "RING-02", "quantity": 1}])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json["unavailable"], ["Test item two"])
        self.assertNotIn("subtotal", response.json)

    def test_mixed_currency_cart_rejected(self):
        client = self.build([self.product(), self.product(sku="RING-02", currency="GBP")])
        response = self.quote(client, lines=[{"sku": "RING-01", "quantity": 1}, {"sku": "RING-02", "quantity": 1}])
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json["checkout_enabled"])

    def test_malformed_unknown_duplicate_and_excess_cart_items_rejected(self):
        client = self.build([self.product()])
        good = {"sku": "RING-01", "quantity": 1}
        for items in ([], ["x"], [{"sku": "MISSING", "quantity": 1}], [good, good],
                      [{"sku": "RING-01", "quantity": True}], [{"sku": "RING-01", "quantity": 21}]):
            with self.subTest(items=items):
                self.assertEqual(self.quote(client, lines=items).status_code, 400)
        self.assertEqual(self.quote(client, country="").status_code, 400)
        self.assertEqual(client.post("/api/cart/preview", json="x" * 9000).status_code, 413)

    def test_invalid_catalog_rejected(self):
        for changed in (
            {"image_url": "javascript:alert(1)"}, {"price_cents": True}, {"price_cents": -1},
            {"sku": "wrong case"}, {"shipping_countries": []}, {"shipping_countries": ["US", "US"]},
            {"shipping_countries": ["WORLDWIDE"]}, {"currency": "JPY"}
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.build([self.product(**changed)])
        with self.assertRaises(ValueError):
            self.build([self.product(), self.product()])


if __name__ == "__main__":
    unittest.main()
