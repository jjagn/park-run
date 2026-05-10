import sqlite3

from config import DB_FILE


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_km    REAL,
                time_str    TEXT,
                pace_str    TEXT,
                ele_gain    REAL,
                intersected_count INTEGER,
                total_score REAL
            )
        """)


def save_run(name, total_km, time_str, pace_str, ele_gain, intersected_count, total_score) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO runs
               (name, total_km, time_str, pace_str, ele_gain, intersected_count, total_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, total_km, time_str, pace_str, ele_gain, intersected_count, total_score),
        )
        return cur.lastrowid


def get_all_runs():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC"
        ).fetchall()


def get_run(run_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
