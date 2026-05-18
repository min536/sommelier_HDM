from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


ROOT = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = ROOT / "sommelier.sqlite3"

# display_order controls menu display sequence (lower = first)
# Food order: 파스타(5) → 소시지(6) → 해시브라운(7) → 오레오베이컨말이(8) → 나초(9) → 치즈케이크(10)
INITIAL_MENU = [
    {"id": 1,  "display_order": 1,  "category": "liquor", "name": "Jaume Serra Cava(스파클링)", "price": 32000, "is_alcohol": True,  "stock": 20,  "img": "sparkling.png", "is_best": False},
    {"id": 2,  "display_order": 2,  "category": "liquor", "name": "Rapel Carilisa Moscato(디저트)", "price": 28000, "is_alcohol": True,  "stock": 40,  "img": "dessert.png",  "is_best": False},
    {"id": 3,  "display_order": 3,  "category": "liquor", "name": "Umani Ronchi Vigor(레드)", "price": 37000, "is_alcohol": True,  "stock": 20,  "img": "red.png",      "is_best": False},
    {"id": 4,  "display_order": 4,  "category": "liquor", "name": "Montford Estate(화이트)", "price": 35000, "is_alcohol": True,  "stock": 20,  "img": "white.png",    "is_best": False},
    {"id": 9,  "display_order": 5,  "category": "food",   "name": "뒥셀 크림 파스타", "price": 23000, "is_alcohol": False, "stock": 50,  "img": "pasta.png",    "is_best": True},
    {"id": 8,  "display_order": 6,  "category": "food",   "name": "소시지 플래터", "price": 19000, "is_alcohol": False, "stock": 50,  "img": "sausage.png",  "is_best": False},
    {"id": 7,  "display_order": 7,  "category": "food",   "name": "해시브라운(3pcs)", "price": 15000, "is_alcohol": False, "stock": 40,  "img": "brown.png",    "is_best": False},
    {"id": 6,  "display_order": 8,  "category": "food",   "name": "오레오베이컨말이(6pcs)", "price": 13000, "is_alcohol": False, "stock": 40,  "img": "oreo.png",     "is_best": True},
    {"id": 5,  "display_order": 9,  "category": "food",   "name": "나쵸 세트", "price": 15000, "is_alcohol": False, "stock": 50,  "img": "nacho.png",    "is_best": False},
    {"id": 10, "display_order": 10, "category": "food",   "name": "치즈케이크", "price": 8000,  "is_alcohol": False, "stock": 30,  "img": "cheeze.png",   "is_best": False},
    {"id": 12, "display_order": 12, "category": "etc",    "name": "물", "price": 1000,  "is_alcohol": False, "stock": 100, "img": "water.png",    "is_best": False},
    {"id": 13, "display_order": 13, "category": "etc",    "name": "프리미엄 와인(판매 이전 운영팀 문의)", "price": 100000, "is_alcohol": True,  "stock": 6,   "img": "premium.png",  "is_best": False},
]

LEGACY_IMAGE_NAME_UPDATES = {
    "Sparkling.png": "sparkling.png",
    "White.png": "white.png",
    "Dessert.jpg": "dessert.png",
    "dessert.jpg": "dessert.png",
    "red.jpg": "red.png",
    "plus.jpg": "plus.png",
    "premium.jpg": "premium.png",
}


def sqlite_path() -> Path:
    configured = os.environ.get("SQLITE_PATH")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_SQLITE_PATH


@contextmanager
def connection():
    path = sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL UNIQUE,
            price INTEGER NOT NULL,
            is_alcohol INTEGER NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            img TEXT NOT NULL,
            is_best INTEGER NOT NULL DEFAULT 0,
            display_order INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dining_tables (
            table_id TEXT PRIMARY KEY,
            entry_time TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id TEXT NOT NULL,
            menu_item_id INTEGER NULL,
            menu_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL,
            is_paid INTEGER NOT NULL DEFAULT 0,
            display_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (table_id) REFERENCES dining_tables(table_id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE SET NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_orders_table_id ON orders(table_id)",
        """
        CREATE TABLE IF NOT EXISTS app_metrics (
            id INTEGER PRIMARY KEY,
            cumulative_revenue INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sales_stats (
            menu_name TEXT PRIMARY KEY,
            quantity INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS order_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_order_id INTEGER UNIQUE,
            table_id TEXT NOT NULL,
            menu_item_id INTEGER NULL,
            menu_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL,
            is_paid INTEGER NOT NULL DEFAULT 0,
            display_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            final_state TEXT NOT NULL DEFAULT 'active',
            cleared_at TEXT NULL,
            cancelled_at TEXT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_order_ledger_created_at ON order_ledger(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_order_ledger_final_state ON order_ledger(final_state)",
    ]
    with connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        for statement in statements:
            conn.execute(statement)
        conn.execute(
            "INSERT OR IGNORE INTO app_metrics (id, cumulative_revenue) VALUES (1, 0)"
        )
        row = conn.execute("SELECT COUNT(*) AS count FROM menu_items").fetchone()
        if row["count"] == 0:
            conn.executemany(
                """
                INSERT INTO menu_items
                (id, category, name, price, is_alcohol, stock, img, is_best, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item["id"],
                        item["category"],
                        item["name"],
                        item["price"],
                        int(item["is_alcohol"]),
                        item["stock"],
                        item["img"],
                        int(item["is_best"]),
                        item["display_order"],
                    )
                    for item in INITIAL_MENU
                ],
            )
        conn.executemany(
            "UPDATE menu_items SET img = ? WHERE img = ?",
            [(current, legacy) for legacy, current in LEGACY_IMAGE_NAME_UPDATES.items()],
        )
        # Migrate existing installations: add display_order column if missing
        try:
            conn.execute("ALTER TABLE menu_items ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Always sync display_order values (idempotent)
        conn.executemany(
            "UPDATE menu_items SET display_order = ? WHERE id = ?",
            [(item["display_order"], item["id"]) for item in INITIAL_MENU],
        )
        # Rename pasta item in existing installations
        conn.execute(
            "UPDATE menu_items SET name = '뒥셀 크림 파스타'"
            " WHERE name IN ('버섯크림 파스타', '버섯 크림 파스타')"
        )
        # Remove 합석 비용 from existing installations
        conn.execute("DELETE FROM menu_items WHERE name = '합석 비용'")
        conn.execute(
            """
            INSERT OR IGNORE INTO order_ledger
            (
                source_order_id, table_id, menu_item_id, menu_name, price,
                status, is_paid, display_time, created_at, final_state
            )
            SELECT
                id, table_id, menu_item_id, menu_name, price,
                status, is_paid, display_time, created_at, 'active'
            FROM orders
            """
        )
        conn.commit()


def _menu_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "category": row["category"],
        "name": row["name"],
        "price": row["price"],
        "is_alcohol": bool(row["is_alcohol"]),
        "stock": row["stock"],
        "img": row["img"],
        "is_best": bool(row["is_best"]),
    }


def get_menu_items(guest_only: bool = False) -> list[dict[str, object]]:
    query = """
        SELECT id, category, name, price, is_alcohol, stock, img, is_best
        FROM menu_items
    """
    params: tuple[object, ...] = ()
    if guest_only:
        query += " WHERE is_alcohol = 0"
    query += " ORDER BY display_order, id"
    with connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_menu_row(row) for row in rows]


def get_table_status(table_id: str) -> dict[str, object]:
    with connection() as conn:
        table = conn.execute(
            "SELECT entry_time FROM dining_tables WHERE table_id = ?",
            (table_id,),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT id, menu_name, price, status, is_paid, display_time
            FROM orders
            WHERE table_id = ?
            ORDER BY id
            """,
            (table_id,),
        ).fetchall()
    if not table:
        return {"orders": []}
    return {
        "entry_time": table["entry_time"],
        "orders": [
            {
                "order_id": row["id"],
                "menu_name": row["menu_name"],
                "price": row["price"],
                "status": row["status"],
                "is_paid": bool(row["is_paid"]),
                "time": row["display_time"],
            }
            for row in rows
        ],
    }


def get_dashboard_data() -> dict[str, object]:
    with connection() as conn:
        menu_rows = conn.execute(
            "SELECT id, category, name, price, is_alcohol, stock, img, is_best FROM menu_items ORDER BY display_order, id"
        ).fetchall()
        metrics = conn.execute(
            "SELECT cumulative_revenue FROM app_metrics WHERE id = 1"
        ).fetchone() or {"cumulative_revenue": 0}
        stat_rows = conn.execute(
            "SELECT menu_name, quantity FROM sales_stats"
        ).fetchall()
        table_rows = conn.execute(
            """
            SELECT
                t.table_id,
                t.entry_time,
                o.id AS order_id,
                o.menu_name,
                o.price,
                o.status,
                o.is_paid,
                o.display_time,
                COALESCE(mi.is_alcohol, 0) AS is_alcohol
            FROM dining_tables t
            LEFT JOIN orders o ON o.table_id = t.table_id
            LEFT JOIN menu_items mi ON mi.id = o.menu_item_id
            ORDER BY CAST(t.table_id AS INTEGER), t.table_id, o.id
            """
        ).fetchall()

    tables: dict[str, dict[str, object]] = {}
    for row in table_rows:
        table_id = row["table_id"]
        tables.setdefault(
            table_id,
            {
                "entry_time": row["entry_time"],
                "orders": [],
                "remaining_bill": 0,
            },
        )
        if row["menu_name"] is None:
            continue
        order = {
            "order_id": row["order_id"],
            "menu_name": row["menu_name"],
            "price": row["price"],
            "status": row["status"],
            "is_paid": bool(row["is_paid"]),
            "time": row["display_time"],
            "is_alcohol": bool(row["is_alcohol"]),
        }
        tables[table_id]["orders"].append(order)
        if not order["is_paid"]:
            tables[table_id]["remaining_bill"] += order["price"]

    return {
        "menu": [_menu_row(row) for row in menu_rows],
        "tables": tables,
        "cumulative_revenue": metrics["cumulative_revenue"],
        "sales_stats": {row["menu_name"]: row["quantity"] for row in stat_rows},
    }


def get_sales_export_data() -> dict[str, object]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id, table_id, menu_name, price, status, is_paid,
                display_time, created_at, final_state, cleared_at, cancelled_at
            FROM order_ledger
            ORDER BY created_at, id
            """
        ).fetchall()
        menu_rows = conn.execute(
            """
            SELECT
                menu_name,
                COUNT(*) AS quantity,
                COALESCE(SUM(price), 0) AS revenue
            FROM order_ledger
            WHERE final_state <> 'cancelled'
            GROUP BY menu_name
            ORDER BY revenue DESC, menu_name
            """
        ).fetchall()
        agg = conn.execute(
            """
            SELECT
                COALESCE(SUM(price), 0) AS ledger_revenue,
                COALESCE(SUM(CASE WHEN is_paid = 0 THEN price ELSE 0 END), 0) AS unpaid_amount
            FROM order_ledger
            WHERE final_state <> 'cancelled'
            """
        ).fetchone()

    orders = [
        {
            "ledger_id": row["id"],
            "table_id": row["table_id"],
            "menu_name": row["menu_name"],
            "price": row["price"],
            "status": row["status"],
            "is_paid": bool(row["is_paid"]),
            "created_at": row["created_at"],
            "final_state": row["final_state"],
            "cleared_at": row["cleared_at"],
            "cancelled_at": row["cancelled_at"],
        }
        for row in rows
    ]
    cancelled_count = sum(1 for o in orders if o["final_state"] == "cancelled")
    unpaid_count = sum(
        1 for o in orders if o["final_state"] != "cancelled" and not o["is_paid"]
    )
    return {
        "ledger_revenue": agg["ledger_revenue"],
        "unpaid_amount": agg["unpaid_amount"],
        "order_count": len(orders) - cancelled_count,
        "cancelled_count": cancelled_count,
        "unpaid_count": unpaid_count,
        "menu_sales": [
            {
                "menu_name": row["menu_name"],
                "quantity": row["quantity"],
                "revenue": row["revenue"],
                "avg_price": round(row["revenue"] / row["quantity"]) if row["quantity"] else 0,
            }
            for row in menu_rows
        ],
        "orders": orders,
    }


def place_order(table_id: str, item_names: list[str]) -> None:
    now = datetime.now(_KST)
    now_iso = now.isoformat()
    with connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT OR IGNORE INTO dining_tables (table_id, entry_time) VALUES (?, ?)",
                (table_id, now_iso),
            )
            for name in item_names:
                item = conn.execute(
                    """
                    SELECT id, price, stock
                    FROM menu_items
                    WHERE name = ?
                    """,
                    (name,),
                ).fetchone()
                if not item or item["stock"] <= 0:
                    raise ValueError(f"[{name}] 항목의 재고가 부족합니다.")
                conn.execute(
                    "UPDATE menu_items SET stock = stock - 1 WHERE id = ?",
                    (item["id"],),
                )
                conn.execute(
                    """
                    INSERT INTO orders
                    (table_id, menu_item_id, menu_name, price, status, is_paid, display_time, created_at)
                    VALUES (?, ?, ?, ?, '대기 중', 0, ?, ?)
                    """,
                    (table_id, item["id"], name, item["price"], now.strftime("%H:%M"), now_iso),
                )
                source_order_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                conn.execute(
                    """
                    INSERT INTO order_ledger
                    (
                        source_order_id, table_id, menu_item_id, menu_name, price,
                        status, is_paid, display_time, created_at, final_state
                    )
                    VALUES (?, ?, ?, ?, ?, '대기 중', 0, ?, ?, 'active')
                    """,
                    (
                        source_order_id,
                        table_id,
                        item["id"],
                        name,
                        item["price"],
                        now.strftime("%H:%M"),
                        now_iso,
                    ),
                )
                conn.execute(
                    "UPDATE app_metrics SET cumulative_revenue = cumulative_revenue + ? WHERE id = 1",
                    (item["price"],),
                )
                conn.execute(
                    """
                    INSERT INTO sales_stats (menu_name, quantity)
                    VALUES (?, 1)
                    ON CONFLICT(menu_name) DO UPDATE SET quantity = quantity + 1
                    """,
                    (name,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def update_menu_item(menu_id: int, price: int, stock: int) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE menu_items SET price = ?, stock = ? WHERE id = ?",
            (price, stock, menu_id),
        )
        conn.commit()


def toggle_item_pay(table_id: str, order_id: int) -> bool:
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM orders WHERE id = ? AND table_id = ?",
            (order_id, table_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            "UPDATE orders SET is_paid = CASE WHEN is_paid = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (order_id,),
        )
        conn.execute(
            """
            UPDATE order_ledger
            SET is_paid = CASE WHEN is_paid = 1 THEN 0 ELSE 1 END
            WHERE source_order_id = ?
            """,
            (order_id,),
        )
        conn.commit()
        return True


def toggle_serve(table_id: str, order_id: int) -> bool:
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM orders WHERE id = ? AND table_id = ?",
            (order_id, table_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            """
            UPDATE orders
            SET status = CASE WHEN status = '대기 중' THEN '서빙 완료' ELSE '대기 중' END
            WHERE id = ?
            """,
            (order_id,),
        )
        conn.execute(
            """
            UPDATE order_ledger
            SET status = CASE WHEN status = '대기 중' THEN '서빙 완료' ELSE '대기 중' END
            WHERE source_order_id = ?
            """,
            (order_id,),
        )
        conn.commit()
        return True


def cancel_order(table_id: str, order_id: int) -> bool:
    with connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT menu_name, price, menu_item_id FROM orders WHERE id = ? AND table_id = ?",
                (order_id, table_id),
            ).fetchone()
            if not item:
                conn.rollback()
                return False
            conn.execute(
                """
                UPDATE order_ledger
                SET final_state = 'cancelled', cancelled_at = ?, source_order_id = NULL
                WHERE source_order_id = ?
                """,
                (datetime.now(_KST).isoformat(), order_id),
            )
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            if item["menu_item_id"] is not None:
                conn.execute(
                    "UPDATE menu_items SET stock = stock + 1 WHERE id = ?",
                    (item["menu_item_id"],),
                )
            conn.execute(
                "UPDATE app_metrics SET cumulative_revenue = cumulative_revenue - ? WHERE id = 1",
                (item["price"],),
            )
            conn.execute(
                """
                UPDATE sales_stats
                SET quantity = CASE WHEN quantity > 0 THEN quantity - 1 ELSE 0 END
                WHERE menu_name = ?
                """,
                (item["menu_name"],),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise


def reset_operation_data() -> None:
    """Delete all operation/order/sales data while preserving menu_items. Idempotent."""
    with connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM dining_tables")
            conn.execute("DELETE FROM order_ledger")
            conn.execute("DELETE FROM sales_stats")
            conn.execute("UPDATE app_metrics SET cumulative_revenue = 0 WHERE id = 1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def clear_table(table_id: str) -> bool:
    with connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            table = conn.execute(
                "SELECT table_id FROM dining_tables WHERE table_id = ?",
                (table_id,),
            ).fetchone()
            if not table:
                conn.rollback()
                return False
            now_iso = datetime.now(_KST).isoformat()
            conn.execute(
                """
                UPDATE order_ledger
                SET final_state = 'cleared', cleared_at = ?, source_order_id = NULL
                WHERE table_id = ? AND final_state = 'active'
                """,
                (now_iso, table_id),
            )
            conn.execute("DELETE FROM dining_tables WHERE table_id = ?", (table_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
