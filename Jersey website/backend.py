from __future__ import annotations

import hmac
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, g, jsonify, request, send_from_directory
from dotenv import load_dotenv
from werkzeug.exceptions import RequestEntityTooLarge

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATABASE_PATH = Path(os.environ.get("DEJ_DATABASE_PATH", BASE_DIR / "instance" / "store.sqlite3"))
PRODUCT_UPLOADS_PATH = Path(os.environ.get("DEJ_PRODUCT_UPLOADS_PATH", BASE_DIR / "images" / "products"))
ADMIN_USERNAME = "OSE"
ADMIN_SESSION_TTL_SECONDS = 8 * 60 * 60
ADMIN_SESSIONS: dict[str, float] = {}
SIZES = ("S", "L", "XL", "XXL")
BADGE_PRICE = 3000
MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024
RETRO_DUPLICATE_TELEGRAM_NUMBERS = frozenset({1, 2, 3, 4, 5, 7, 10, 15, 16, 17, 26, 29, 30, 31, 35})
RETRO_DUPLICATE_PRODUCT_IDS = frozenset(
    f"telegram-{number:02d}" for number in RETRO_DUPLICATE_TELEGRAM_NUMBERS
)


def build_catalog() -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    for number in range(1, 36):
        if number in RETRO_DUPLICATE_TELEGRAM_NUMBERS:
            continue
        is_england = number in (8, 19)
        is_spain = number == 23
        is_nigeria = number == 32
        is_national = is_england or is_spain or is_nigeria
        if is_england:
            name = f"England National Team Shirt {'01' if number == 8 else '02'}"
            team = "England"
        elif is_spain:
            name, team = "Spain National Team Shirt 01", "Spain"
        elif is_nigeria:
            name, team = "Nigeria National Team Jersey", "Nigeria"
        else:
            name, team = f"Club Jersey {number:02d}", "Club selection"

        products.append({
            "id": f"telegram-{number:02d}",
            "sku": f"DEJ-{number:04d}",
            "name": name,
            "team": team,
            "category": "national" if is_national else "club",
            "price": 24000 if number in (6, 9) else 18000,
            "currency": "NGN",
            "image": f"images/jerseys/photo_{number}_2026-10-17_00-41-31.jpg",
            "isNewArrival": number >= 30 or is_national,
            "source": "telegram-import",
        })

    new_national = [
        ("Brazil", "Brazil National Team Away Jersey"),
        ("France", "France National Team Jersey"),
        ("Brazil", "Brazil National Team Home Jersey"),
        ("Morocco", "Morocco National Team Away Jersey"),
        ("Morocco", "Morocco National Team Home Jersey"),
        ("Brazil", "Brazil National Team Jersey and Shorts Set"),
        ("Germany", "Germany National Team Jersey"),
        ("Argentina", "Argentina National Team Jersey"),
        ("England", "England National Team Red Away Jersey"),
        ("Italy", "Italy National Team Jersey"),
    ]
    for number, (team, name) in enumerate(new_national, start=1):
        products.append({
            "id": f"national-new-{number:02d}",
            "sku": f"DEJ-NT-{number:04d}",
            "name": name,
            "team": team,
            "category": "national",
            "price": 18000,
            "currency": "NGN",
            "image": f"images/jerseys/photo_{number}_2026-10-17_10-44-53.jpg",
            "isNewArrival": True,
            "source": "user-upload",
        })

    products.append({
        "id": "real-madrid-dark-green",
        "sku": "DEJ-RM-GREEN-01",
        "name": "Real Madrid Dark Green Jersey",
        "team": "Real Madrid",
        "category": "club",
        "price": 18000,
        "currency": "NGN",
        "image": "images/real-madrid-jersey.jpg",
        "isNewArrival": True,
        "source": "user-upload",
    })

    for number in range(1, 16):
        products.append({
            "id": f"retro-{number:02d}",
            "sku": f"DEJ-RETRO-{number:04d}",
            "name": f"Retro Jersey {number:02d}",
            "team": "Retro collection",
            "category": "club",
            "price": 24000,
            "currency": "NGN",
            "image": f"images/Retro jersey/photo_{number}_2026-10-22_21-11-39.jpg",
            "isNewArrival": False,
            "source": "user-upload",
        })
    return products


PRODUCT_CATALOG = build_catalog()
app = Flask(__name__, static_folder=None)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_PRODUCT_IMAGE_BYTES + 512 * 1024


def connect_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_database() -> sqlite3.Connection:
    if "database" not in g:
        g.database = connect_database()
    return g.database


@app.teardown_appcontext
def close_database(_error: BaseException | None) -> None:
    connection = g.pop("database", None)
    if connection is not None:
        connection.close()


def initialize_database() -> None:
    connection = connect_database()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                team TEXT NOT NULL,
                category TEXT NOT NULL CHECK (category IN ('club', 'national')),
                price INTEGER NOT NULL CHECK (price >= 0),
                currency TEXT NOT NULL,
                image TEXT NOT NULL,
                is_new_arrival INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inventory (
                product_id TEXT NOT NULL REFERENCES products(id),
                size TEXT NOT NULL CHECK (size IN ('S', 'L', 'XL', 'XXL')),
                quantity INTEGER CHECK (quantity IS NULL OR quantity >= 0),
                PRIMARY KEY (product_id, size)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL UNIQUE,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_confirmation',
                subtotal INTEGER NOT NULL CHECK (subtotal >= 0),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL REFERENCES products(id),
                product_name TEXT NOT NULL,
                sku TEXT NOT NULL,
                size TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                badge TEXT NOT NULL,
                badge_text TEXT NOT NULL DEFAULT '',
                unit_price INTEGER NOT NULL CHECK (unit_price >= 0)
            );
            CREATE INDEX IF NOT EXISTS orders_status_created ON orders(status, created_at);
            """
        )
        product_columns = {
            column["name"] for column in connection.execute("PRAGMA table_info(products)")
        }
        if "is_active" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        with connection:
            for product in PRODUCT_CATALOG:
                connection.execute(
                    """INSERT OR IGNORE INTO products
                       (id, sku, name, team, category, price, currency, image, is_new_arrival, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        product["id"], product["sku"], product["name"], product["team"],
                        product["category"], product["price"], product["currency"],
                        product["image"], int(product["isNewArrival"]), product["source"],
                    ),
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO inventory (product_id, size, quantity) VALUES (?, ?, NULL)",
                    [(product["id"], size) for size in SIZES],
                )
            connection.executemany(
                "UPDATE products SET price = 24000 WHERE id = ?",
                [("telegram-06",), ("telegram-09",)],
            )
    finally:
        connection.close()


def admin_required(handler: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(handler)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        supplied = request.headers.get("X-Admin-Token", "")
        expires_at = ADMIN_SESSIONS.get(supplied, 0)
        if not supplied or expires_at <= time.monotonic():
            ADMIN_SESSIONS.pop(supplied, None)
            return jsonify({"error": "Admin authorization failed."}), 401
        return handler(*args, **kwargs)
    return wrapped


def product_from_row(row: sqlite3.Row, connection: sqlite3.Connection) -> dict[str, Any]:
    product = dict(row)
    product["isNewArrival"] = bool(product.pop("is_new_arrival"))
    product["isActive"] = bool(product.pop("is_active"))
    product["stockBySize"] = {
        stock["size"]: stock["quantity"]
        for stock in connection.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product["id"],)
        )
    }
    tracked_sizes = [size for size, quantity in product["stockBySize"].items() if quantity is not None]
    product["stockTracked"] = bool(tracked_sizes)
    product["availableSizes"] = (
        [size for size in SIZES if (product["stockBySize"].get(size) or 0) > 0]
        if tracked_sizes else list(SIZES)
    )
    return product


def json_error(message: str, status: int) -> tuple[Any, int]:
    return jsonify({"error": message}), status


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error: RequestEntityTooLarge) -> tuple[Any, int]:
    return json_error("The upload is too large. Jersey images must be 5 MB or smaller.", 413)


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "service": "desmond-empire-jerseys"})


@app.post("/api/admin/login")
def admin_login() -> Any:
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", ""))
    valid_username = hmac.compare_digest(username.encode("utf-8"), ADMIN_USERNAME.encode("utf-8"))
    if not valid_username:
        return json_error("Username is incorrect.", 401)

    now = time.monotonic()
    expired_sessions = [token for token, expires_at in ADMIN_SESSIONS.items() if expires_at <= now]
    for token in expired_sessions:
        ADMIN_SESSIONS.pop(token, None)
    session_token = secrets.token_urlsafe(32)
    ADMIN_SESSIONS[session_token] = now + ADMIN_SESSION_TTL_SECONDS
    return jsonify({"token": session_token, "expiresIn": ADMIN_SESSION_TTL_SECONDS})


@app.get("/api/products")
def list_products() -> Any:
    connection = get_database()
    placeholders = ", ".join("?" for _ in RETRO_DUPLICATE_PRODUCT_IDS)
    rows = connection.execute(
                f"""SELECT * FROM products
                        WHERE is_active = 1
                            AND id NOT IN ({placeholders})
                            AND (
                                NOT EXISTS (SELECT 1 FROM inventory tracked WHERE tracked.product_id = products.id AND tracked.quantity IS NOT NULL)
                                OR EXISTS (SELECT 1 FROM inventory available WHERE available.product_id = products.id AND available.quantity > 0)
                            )
                        ORDER BY sku""",
        tuple(RETRO_DUPLICATE_PRODUCT_IDS),
    ).fetchall()
    return jsonify([product_from_row(row, connection) for row in rows])


@app.post("/api/orders")
def create_order() -> Any:
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    address = str(data.get("address", "")).strip()
    items = data.get("items")
    if not name or len(name) > 100:
        return json_error("Enter a name up to 100 characters.", 400)
    if not phone or len(phone) > 40:
        return json_error("Enter a valid phone number.", 400)
    if not address or len(address) > 500:
        return json_error("Enter a delivery address up to 500 characters.", 400)
    if not isinstance(items, list) or not items or len(items) > 30:
        return json_error("Add between 1 and 30 order lines.", 400)

    connection = get_database()
    order_lines: list[dict[str, Any]] = []
    requested_stock: dict[tuple[str, str], int] = {}
    subtotal = 0
    for item in items:
        if not isinstance(item, dict):
            return json_error("Each order line must be an object.", 400)
        product_id = str(item.get("product_id", ""))
        if product_id in RETRO_DUPLICATE_PRODUCT_IDS:
            return json_error("This duplicate jersey is no longer available. Choose its Retro collection listing instead.", 404)
        size = str(item.get("size", ""))
        quantity = item.get("quantity")
        badge = str(item.get("badge", "none"))
        badge_text = str(item.get("custom_text", "")).strip()
        if size not in SIZES or not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 100:
            return json_error("Each order line needs a supported size and quantity from 1 to 100.", 400)
        product_row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product_row is None:
            return json_error("A selected jersey could not be found.", 404)
        product = dict(product_row)
        if not product["is_active"]:
            return json_error("This jersey is no longer available.", 409)
        if badge not in {"none", "premier-league", "champions-league", "custom"}:
            return json_error("Choose a valid badge option.", 400)
        if product["category"] == "national" and badge != "none":
            return json_error("Badge customization is not available for national-team jerseys.", 400)
        if product["category"] == "club" and badge == "custom" and (not badge_text or len(badge_text) > 100):
            return json_error("Describe the custom badge in 1 to 100 characters.", 400)

        stock = connection.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, size)
        ).fetchone()
        if stock is None:
            return json_error("Stock information for this size is unavailable.", 409)
        if stock["quantity"] is not None and stock["quantity"] < quantity:
            return json_error(f"Not enough stock for {product['name']} in size {size}.", 409)

        requested_stock[(product_id, size)] = requested_stock.get((product_id, size), 0) + quantity
        badge_price = BADGE_PRICE if product["category"] == "club" and badge != "none" else 0
        unit_price = product["price"] + badge_price
        subtotal += unit_price * quantity
        order_lines.append({
            "product": product,
            "size": size,
            "quantity": quantity,
            "badge": badge,
            "badge_text": badge_text if badge == "custom" else "",
            "unit_price": unit_price,
        })

    for (product_id, size), quantity in requested_stock.items():
        stock = connection.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, size)
        ).fetchone()
        if stock["quantity"] is not None and stock["quantity"] < quantity:
            return json_error("Requested quantity exceeds the remaining stock for a jersey size.", 409)

    reference = f"DEJ-{secrets.token_hex(4).upper()}"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection:
        cursor = connection.execute(
            """INSERT INTO orders (reference, customer_name, customer_phone, delivery_address, subtotal, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (reference, name, phone, address, subtotal, created_at),
        )
        order_id = cursor.lastrowid
        connection.executemany(
            """INSERT INTO order_items
               (order_id, product_id, product_name, sku, size, quantity, badge, badge_text, unit_price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (order_id, line["product"]["id"], line["product"]["name"], line["product"]["sku"],
                 line["size"], line["quantity"], line["badge"], line["badge_text"], line["unit_price"])
                for line in order_lines
            ],
        )
    return jsonify({"reference": reference, "status": "pending_confirmation", "subtotal": subtotal}), 201


@app.get("/api/admin/products")
@admin_required
def admin_products() -> Any:
    connection = get_database()
    placeholders = ", ".join("?" for _ in RETRO_DUPLICATE_PRODUCT_IDS)
    rows = connection.execute(
        f"SELECT * FROM products WHERE id NOT IN ({placeholders}) ORDER BY is_active DESC, sku",
        tuple(RETRO_DUPLICATE_PRODUCT_IDS),
    ).fetchall()
    return jsonify([product_from_row(row, connection) for row in rows])


@app.post("/api/admin/products")
@admin_required
def create_product() -> Any:
    name = request.form.get("name", "").strip()
    team = request.form.get("team", "").strip()
    category = request.form.get("category", "")
    price_text = request.form.get("price", "")
    image_file = request.files.get("image")

    if not name or len(name) > 120:
        return json_error("Enter a jersey name up to 120 characters.", 400)
    if not team or len(team) > 80:
        return json_error("Enter a team or collection name up to 80 characters.", 400)
    if category not in {"club", "national"}:
        return json_error("Choose Club or National team.", 400)
    if not price_text.isdigit() or not 1 <= int(price_text) <= 100_000_000:
        return json_error("Enter a price greater than zero.", 400)
    stock: dict[str, int] = {}
    for size in SIZES:
        quantity_text = request.form.get(f"stock_{size}", "")
        if not quantity_text.isdigit() or int(quantity_text) > 1_000_000:
            return json_error(f"Enter a whole stock quantity from 0 to 1,000,000 for size {size}.", 400)
        stock[size] = int(quantity_text)
    if not any(stock.values()):
        return json_error("Add at least one available size with stock greater than 0.", 400)
    if image_file is None or not image_file.filename:
        return json_error("Choose a jersey image to upload.", 400)

    image_data = image_file.stream.read(MAX_PRODUCT_IMAGE_BYTES + 1)
    if len(image_data) > MAX_PRODUCT_IMAGE_BYTES:
        return json_error("Jersey images must be 5 MB or smaller.", 413)
    image_formats = (
        (b"\xff\xd8\xff", ".jpg"),
        (b"\x89PNG\r\n\x1a\n", ".png"),
    )
    image_extension = next((extension for signature, extension in image_formats if image_data.startswith(signature)), None)
    if image_extension is None and len(image_data) >= 12 and image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        image_extension = ".webp"
    if image_extension is None:
        return json_error("Upload a valid JPEG, PNG, or WebP image.", 400)

    product_id = f"manual-{secrets.token_hex(8)}"
    sku = f"DEJ-MAN-{product_id.removeprefix('manual-').upper()}"
    image_directory = PRODUCT_UPLOADS_PATH
    image_directory.mkdir(parents=True, exist_ok=True)
    image_name = f"{uuid.uuid4().hex}{image_extension}"
    image_path = image_directory / image_name
    image_path.write_bytes(image_data)
    relative_image_path = f"images/products/{image_name}"

    connection = get_database()
    try:
        with connection:
            connection.execute(
                """INSERT INTO products
                   (id, sku, name, team, category, price, currency, image, is_new_arrival, is_active, source)
                   VALUES (?, ?, ?, ?, ?, ?, 'NGN', ?, ?, 1, 'admin-upload')""",
                (product_id, sku, name, team, category, int(price_text), relative_image_path,
                 int(request.form.get("isNewArrival") == "true")),
            )
            connection.executemany(
                "INSERT INTO inventory (product_id, size, quantity) VALUES (?, ?, ?)",
                [(product_id, size, stock[size]) for size in SIZES],
            )
    except sqlite3.IntegrityError:
        image_path.unlink(missing_ok=True)
        return json_error("That jersey could not be added. Check its details and try again.", 409)

    row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(product_from_row(row, connection)), 201


@app.patch("/api/admin/products/<path:product_id>/availability")
@admin_required
def update_product_availability(product_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    is_active = data.get("isActive")
    if not isinstance(is_active, bool):
        return json_error("Choose whether the jersey is available for sale.", 400)
    connection = get_database()
    product = connection.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        return json_error("Product not found.", 404)
    if is_active:
        stock_rows = connection.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
        has_tracked_stock = any(row["quantity"] is not None for row in stock_rows)
        has_available_stock = any((row["quantity"] or 0) > 0 for row in stock_rows)
        if has_tracked_stock and not has_available_stock:
            return json_error("Add stock to at least one size and save it before restoring this jersey to the shop.", 409)
    with connection:
        result = connection.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (int(is_active), product_id),
        )
    row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(product_from_row(row, connection))


@app.patch("/api/admin/products/<path:product_id>/stock")
@admin_required
def update_stock(product_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    stock_data = data.get("stock")
    if not isinstance(stock_data, dict) or not stock_data:
        return json_error("Provide size quantities in a stock object.", 400)
    connection = get_database()
    if connection.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone() is None:
        return json_error("Product not found.", 404)
    updates: list[tuple[str, int | None]] = []
    for size, quantity in stock_data.items():
        if size not in SIZES:
            return json_error(f"Unsupported size: {size}.", 400)
        if quantity is not None and (not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0):
            return json_error("Stock quantities must be non-negative whole numbers or null for untracked stock.", 400)
        updates.append((size, quantity))
    with connection:
        for size, quantity in updates:
            connection.execute(
                "UPDATE inventory SET quantity = ? WHERE product_id = ? AND size = ?",
                (quantity, product_id, size),
            )
    row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(product_from_row(row, connection))


@app.get("/api/admin/orders")
@admin_required
def admin_orders() -> Any:
    connection = get_database()
    orders = connection.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 200").fetchall()
    result: list[dict[str, Any]] = []
    for order_row in orders:
        order = dict(order_row)
        order["items"] = [dict(row) for row in connection.execute(
            "SELECT product_name, sku, size, quantity, badge, badge_text, unit_price FROM order_items WHERE order_id = ?",
            (order["id"],),
        )]
        result.append(order)
    return jsonify(result)


@app.patch("/api/admin/orders/<reference>")
@admin_required
def update_order(reference: str) -> Any:
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in {"confirmed", "dispatched", "completed", "cancelled"}:
        return json_error("Choose a supported order status.", 400)
    connection = get_database()
    order = connection.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    if order is None:
        return json_error("Order not found.", 404)

    current_status = order["status"]
    allowed_transitions = {
        "pending_confirmation": {"confirmed", "cancelled"},
        "confirmed": {"dispatched", "cancelled"},
        "dispatched": {"completed"},
        "completed": set(),
        "cancelled": set(),
    }
    if new_status not in allowed_transitions[current_status]:
        return json_error(f"Cannot move an order from {current_status} to {new_status}.", 409)

    lines = connection.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
    try:
        with connection:
            if new_status == "confirmed":
                needed: dict[tuple[str, str], int] = {}
                for line in lines:
                    key = (line["product_id"], line["size"])
                    needed[key] = needed.get(key, 0) + line["quantity"]
                for (product_id, size), quantity in needed.items():
                    stock = connection.execute(
                        "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?",
                        (product_id, size),
                    ).fetchone()
                    if stock is None or stock["quantity"] is None:
                        raise ValueError("Enter tracked stock for every ordered size before confirming this order.")
                    if stock["quantity"] < quantity:
                        raise ValueError(f"Not enough stock in size {size} to confirm this order.")
                for (product_id, size), quantity in needed.items():
                    connection.execute(
                        "UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND size = ?",
                        (quantity, product_id, size),
                    )
            elif new_status == "cancelled" and current_status == "confirmed":
                for line in lines:
                    connection.execute(
                        "UPDATE inventory SET quantity = quantity + ? WHERE product_id = ? AND size = ? AND quantity IS NOT NULL",
                        (line["quantity"], line["product_id"], line["size"]),
                    )
            connection.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order["id"]))
    except ValueError as error:
        return json_error(str(error), 409)
    return jsonify({"reference": reference, "status": new_status})


@app.get("/")
def home() -> Any:
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:asset_path>")
def serve_site_asset(asset_path: str) -> Any:
    return send_from_directory(BASE_DIR, asset_path)


@app.get("/images/products/<path:filename>")
def serve_uploaded_product_image(filename: str) -> Any:
    return send_from_directory(PRODUCT_UPLOADS_PATH, filename)


initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)