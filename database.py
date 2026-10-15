
# database.py

"""SQLite schema and connection helpers; values are always parameterized."""

import sqlite3
from pathlib import Path

from config import DATABASE_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_json TEXT NOT NULL,
    source TEXT NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shortlist (
    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    notes TEXT NOT NULL DEFAULT '',
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_cache (
    cache_key TEXT PRIMARY KEY,
    results_json TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_cache_expires_at
    ON search_cache(expires_at);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys and WAL enabled."""
    db_path = Path(path) if path else DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database(path: Path | str | None = None) -> None:
    """Create any missing application tables without deleting existing data."""
    with connect(path) as conn:
        conn.executescript(SCHEMA)

