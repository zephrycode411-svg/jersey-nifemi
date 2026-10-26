from __future__ import annotations

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

_test_directory = tempfile.TemporaryDirectory()
os.environ["DEJ_DATABASE_PATH"] = str(Path(_test_directory.name) / "shop-test.sqlite3")
import backend


class StoreApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database_directory = tempfile.TemporaryDirectory()
        backend.DATABASE_PATH = Path(self.database_directory.name) / "shop.sqlite3"
        backend.PRODUCT_UPLOADS_PATH = Path(self.database_directory.name) / "uploads"
        backend.ADMIN_SESSIONS.clear()
        backend.initialize_database()
        self.client = backend.app.test_client()
        login = self.client.post("/api/admin/login", json={
            "username": "OSE",
        })
        self.admin_headers = {"X-Admin-Token": login.get_json()["token"]}

    def tearDown(self) -> None:
        self.database_directory.cleanup()

    def test_stock_and_order_lifecycle(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)

        products_response = self.client.get("/api/products")
        self.assertEqual(products_response.status_code, 200)
        products = products_response.get_json()
        self.assertEqual(len(products), 46)
        priced_club_jerseys = {product["id"]: product["price"] for product in products}
        self.assertEqual(priced_club_jerseys["telegram-06"], 24000)
        self.assertEqual(priced_club_jerseys["telegram-09"], 24000)
        retro_jerseys = [product for product in products if product["id"].startswith("retro-")]
        self.assertEqual(len(retro_jerseys), 15)
        self.assertTrue(all(product["price"] == 24000 for product in retro_jerseys))
        self.assertFalse(any(product["id"] in backend.RETRO_DUPLICATE_PRODUCT_IDS for product in products))
        madrid = next(product for product in products if product["id"] == "real-madrid-dark-green")
        self.assertFalse(madrid["stockTracked"])

        unauthorized = self.client.get("/api/admin/products")
        self.assertEqual(unauthorized.status_code, 401)

        stock_update = self.client.patch(
            "/api/admin/products/real-madrid-dark-green/stock",
            headers=self.admin_headers,
            json={"stock": {"S": 3, "L": 2, "XL": 0, "XXL": None}},
        )
        self.assertEqual(stock_update.status_code, 200)
        self.assertEqual(stock_update.get_json()["availableSizes"], ["S", "L"])

        order_response = self.client.post(
            "/api/orders",
            json={
                "name": "Test Customer",
                "phone": "08000000000",
                "address": "Lagos",
                "items": [{
                    "product_id": "real-madrid-dark-green",
                    "size": "S",
                    "quantity": 2,
                    "badge": "premier-league",
                }],
            },
        )
        self.assertEqual(order_response.status_code, 201)
        order = order_response.get_json()
        self.assertEqual(order["subtotal"], 42000)
        self.assertEqual(order["status"], "pending_confirmation")

        confirmed = self.client.patch(
            f"/api/admin/orders/{order['reference']}",
            headers=self.admin_headers,
            json={"status": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        refreshed = self.client.get("/api/products").get_json()
        madrid = next(product for product in refreshed if product["id"] == "real-madrid-dark-green")
        self.assertEqual(madrid["stockBySize"]["S"], 1)

        cancelled = self.client.patch(
            f"/api/admin/orders/{order['reference']}",
            headers=self.admin_headers,
            json={"status": "cancelled"},
        )
        self.assertEqual(cancelled.status_code, 200)
        refreshed = self.client.get("/api/products").get_json()
        madrid = next(product for product in refreshed if product["id"] == "real-madrid-dark-green")
        self.assertEqual(madrid["stockBySize"]["S"], 3)

    def test_retro_jerseys_are_added_to_existing_database(self) -> None:
        connection = backend.connect_database()
        try:
            with connection:
                connection.execute("DELETE FROM inventory WHERE product_id LIKE 'retro-%'")
                connection.execute("DELETE FROM products WHERE id LIKE 'retro-%'")
        finally:
            connection.close()

        backend.initialize_database()
        products = self.client.get("/api/products").get_json()
        retro_jerseys = [product for product in products if product["id"].startswith("retro-")]
        self.assertEqual(len(retro_jerseys), 15)
        self.assertEqual(retro_jerseys[0]["image"], "images/Retro jersey/photo_1_2026-10-22_21-11-39.jpg")
        self.assertTrue(all(product["price"] == 24000 for product in retro_jerseys))

    def test_national_jerseys_reject_badges(self) -> None:
        response = self.client.post(
            "/api/orders",
            json={
                "name": "Test Customer",
                "phone": "08000000000",
                "address": "Lagos",
                "items": [{
                    "product_id": "national-new-01",
                    "size": "L",
                    "quantity": 1,
                    "badge": "champions-league",
                }],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_retro_duplicate_jersey_cannot_be_ordered(self) -> None:
        duplicate_id = next(iter(backend.RETRO_DUPLICATE_PRODUCT_IDS))
        response = self.client.post(
            "/api/orders",
            json={
                "name": "Test Customer",
                "phone": "08000000000",
                "address": "Lagos",
                "items": [{
                    "product_id": duplicate_id,
                    "size": "L",
                    "quantity": 1,
                }],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_username_only_login_issues_admin_session(self) -> None:
        accepted = self.client.post("/api/admin/login", json={
            "username": "OSE",
        })
        rejected = self.client.post("/api/admin/login", json={
            "username": "incorrect-user",
        })
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(self.client.get("/api/admin/products").status_code, 401)
        token = accepted.get_json()["token"]
        authorized = self.client.get("/api/admin/products", headers={"X-Admin-Token": token})
        self.assertEqual(authorized.status_code, 200)

    def test_admin_can_add_and_archive_a_jersey(self) -> None:
        created = self.client.post(
            "/api/admin/products",
            headers=self.admin_headers,
            data={
                "name": "Lagos Test Jersey",
                "team": "Lagos FC",
                "category": "club",
                "price": "22000",
                "stock_S": "2",
                "stock_L": "1",
                "stock_XL": "0",
                "stock_XXL": "0",
                "isNewArrival": "true",
                "image": (BytesIO(b"\x89PNG\r\n\x1a\nvalid-test-image"), "jersey.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(created.status_code, 201)
        product = created.get_json()
        self.assertTrue(product["image"].startswith("images/products/"))
        uploaded_image = self.client.get(product["image"])
        self.assertEqual(uploaded_image.status_code, 200)
        self.assertEqual(uploaded_image.data, b"\x89PNG\r\n\x1a\nvalid-test-image")
        self.assertTrue(product["isActive"])
        self.assertTrue(product["isNewArrival"])
        self.assertEqual(product["availableSizes"], ["S", "L"])
        public_ids = {item["id"] for item in self.client.get("/api/products").get_json()}
        self.assertIn(product["id"], public_ids)

        archived = self.client.patch(
            f"/api/admin/products/{product['id']}/availability",
            headers=self.admin_headers,
            json={"isActive": False},
        )
        self.assertEqual(archived.status_code, 200)
        self.assertFalse(archived.get_json()["isActive"])
        public_ids = {item["id"] for item in self.client.get("/api/products").get_json()}
        self.assertNotIn(product["id"], public_ids)

        restored = self.client.patch(
            f"/api/admin/products/{product['id']}/availability",
            headers=self.admin_headers,
            json={"isActive": True},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertIn(product["id"], {item["id"] for item in self.client.get("/api/products").get_json()})

    def test_restore_requires_available_stock(self) -> None:
        created = self.client.post(
            "/api/admin/products",
            headers=self.admin_headers,
            data={
                "name": "Restore Stock Jersey",
                "team": "Test FC",
                "category": "club",
                "price": "18000",
                "stock_S": "1",
                "stock_L": "0",
                "stock_XL": "0",
                "stock_XXL": "0",
                "image": (BytesIO(b"\x89PNG\r\n\x1a\nvalid-test-image"), "jersey.png"),
            },
            content_type="multipart/form-data",
        )
        product = created.get_json()
        self.client.patch(
            f"/api/admin/products/{product['id']}/availability",
            headers=self.admin_headers,
            json={"isActive": False},
        )
        self.client.patch(
            f"/api/admin/products/{product['id']}/stock",
            headers=self.admin_headers,
            json={"stock": {"S": 0, "L": 0, "XL": 0, "XXL": 0}},
        )

        blocked = self.client.patch(
            f"/api/admin/products/{product['id']}/availability",
            headers=self.admin_headers,
            json={"isActive": True},
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("Add stock to at least one size", blocked.get_json()["error"])

        self.client.patch(
            f"/api/admin/products/{product['id']}/stock",
            headers=self.admin_headers,
            json={"stock": {"S": 2, "L": 0, "XL": 0, "XXL": 0}},
        )
        restored = self.client.patch(
            f"/api/admin/products/{product['id']}/availability",
            headers=self.admin_headers,
            json={"isActive": True},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertIn(product["id"], {item["id"] for item in self.client.get("/api/products").get_json()})

    def test_admin_upload_rejects_unsupported_image(self) -> None:
        response = self.client.post(
            "/api/admin/products",
            headers=self.admin_headers,
            data={
                "name": "Invalid Jersey",
                "team": "Test FC",
                "category": "club",
                "price": "18000",
                "stock_S": "1",
                "stock_L": "0",
                "stock_XL": "0",
                "stock_XXL": "0",
                "image": (BytesIO(b"not an image"), "jersey.svg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_new_jersey_requires_available_stock(self) -> None:
        response = self.client.post(
            "/api/admin/products",
            headers=self.admin_headers,
            data={
                "name": "Sold Out Jersey",
                "team": "Test FC",
                "category": "club",
                "price": "18000",
                "stock_S": "0",
                "stock_L": "0",
                "stock_XL": "0",
                "stock_XXL": "0",
                "image": (BytesIO(b"\x89PNG\r\n\x1a\nvalid-test-image"), "jersey.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one available size", response.get_json()["error"])

    def test_confirmed_last_unit_hides_jersey_and_cancellation_restores_it(self) -> None:
        created = self.client.post(
            "/api/admin/products",
            headers=self.admin_headers,
            data={
                "name": "Last Unit Jersey",
                "team": "Test FC",
                "category": "club",
                "price": "18000",
                "stock_S": "1",
                "stock_L": "0",
                "stock_XL": "0",
                "stock_XXL": "0",
                "image": (BytesIO(b"\x89PNG\r\n\x1a\nvalid-test-image"), "jersey.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(created.status_code, 201)
        product = created.get_json()
        order_response = self.client.post(
            "/api/orders",
            json={
                "name": "Test Customer",
                "phone": "08000000000",
                "address": "Lagos",
                "items": [{"product_id": product["id"], "size": "S", "quantity": 1}],
            },
        )
        self.assertEqual(order_response.status_code, 201)
        reference = order_response.get_json()["reference"]

        confirmed = self.client.patch(
            f"/api/admin/orders/{reference}",
            headers=self.admin_headers,
            json={"status": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200)
        public_ids = {item["id"] for item in self.client.get("/api/products").get_json()}
        self.assertNotIn(product["id"], public_ids)

        cancelled = self.client.patch(
            f"/api/admin/orders/{reference}",
            headers=self.admin_headers,
            json={"status": "cancelled"},
        )
        self.assertEqual(cancelled.status_code, 200)
        public_ids = {item["id"] for item in self.client.get("/api/products").get_json()}
        self.assertIn(product["id"], public_ids)


if __name__ == "__main__":
    unittest.main()