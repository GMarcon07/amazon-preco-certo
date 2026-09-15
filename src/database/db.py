import sqlite3
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asin TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    category_id TEXT NOT NULL,
    rating REAL DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    seller_name TEXT,
    is_prime INTEGER DEFAULT 0,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asin TEXT NOT NULL,
    price REAL NOT NULL,
    strikethrough_price REAL,
    discount_pct REAL,
    seller_name TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(asin) REFERENCES products(asin) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at);

CREATE TABLE IF NOT EXISTS alerts_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asin TEXT NOT NULL,
    price_at_alert REAL NOT NULL,
    reference_price REAL NOT NULL,
    discount_pct REAL NOT NULL,
    anomaly_type TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    FOREIGN KEY(asin) REFERENCES products(asin) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_asin_date ON alerts_history(asin, sent_at);
"""


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
