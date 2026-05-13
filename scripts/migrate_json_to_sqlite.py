from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import connection, init_db, sqlite_path


DATA_FILE = ROOT / "data.json"


def migrate() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing source file: {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    init_db()

    with connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM dining_tables")
            conn.execute("DELETE FROM sales_stats")
            conn.execute("DELETE FROM menu_items")

            menu_rows = [
                (
                    item["id"],
                    item["category"],
                    item["name"],
                    item["price"],
                    int(bool(item.get("is_alcohol"))),
                    item["stock"],
                    item["img"],
                    int(bool(item.get("is_best"))),
                )
                for item in data.get("menu", [])
            ]
            if menu_rows:
                conn.executemany(
                    """
                    INSERT INTO menu_items
                    (id, category, name, price, is_alcohol, stock, img, is_best)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    menu_rows,
                )

            for table_id, table in data.get("tables", {}).items():
                entry_time = table.get("entry_time") or ""
                conn.execute(
                    "INSERT INTO dining_tables (table_id, entry_time) VALUES (?, ?)",
                    (table_id, entry_time),
                )
                for order in table.get("orders", []):
                    menu_item = conn.execute(
                        "SELECT id FROM menu_items WHERE name = ?",
                        (order.get("menu_name"),),
                    ).fetchone()
                    conn.execute(
                        """
                        INSERT INTO orders
                        (table_id, menu_item_id, menu_name, price, status, is_paid, display_time, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            table_id,
                            None if not menu_item else menu_item["id"],
                            order["menu_name"],
                            order["price"],
                            order.get("status", "대기 중"),
                            int(bool(order.get("is_paid"))),
                            order.get("time", ""),
                            entry_time,
                        ),
                    )

            conn.execute(
                "UPDATE app_metrics SET cumulative_revenue = ? WHERE id = 1",
                (data.get("cumulative_revenue", 0),),
            )
            sales_rows = [
                (name, qty)
                for name, qty in data.get("sales_stats", {}).items()
            ]
            if sales_rows:
                conn.executemany(
                    "INSERT INTO sales_stats (menu_name, quantity) VALUES (?, ?)",
                    sales_rows,
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    migrate()
    print(f"data.json migrated to SQLite: {sqlite_path()}")

