from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import init_db, sqlite_path


if __name__ == "__main__":
    init_db()
    print(f"SQLite schema is ready: {sqlite_path()}")

