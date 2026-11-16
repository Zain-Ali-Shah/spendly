import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)


def get_db():
    """Return a SQLite connection with row access by name and FKs enforced."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and sample expenses (amounts in PKR) once."""
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Demo User",
                "demo@spendly.com",
                generate_password_hash("demo123"),
            ),
        )
        user_id = cursor.lastrowid

        today = date.today()

        def day(number):
            return today.replace(day=number).isoformat()

        expenses = [
            (user_id, 1250.00, "Food", day(2), "Groceries"),
            (user_id, 800.00, "Transport", day(4), "Fuel"),
            (user_id, 6500.00, "Bills", day(6), "Electricity bill"),
            (user_id, 1500.00, "Health", day(9), "Pharmacy"),
            (user_id, 2000.00, "Entertainment", day(12), "Cinema tickets"),
            (user_id, 4500.00, "Shopping", day(15), "Clothes"),
            (user_id, 700.00, "Other", day(18), "Miscellaneous"),
            (user_id, 950.00, "Food", day(22), "Dinner out"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
