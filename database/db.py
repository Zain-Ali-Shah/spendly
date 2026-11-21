import os
import secrets
import sqlite3
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get(
    "SPENDLY_DB_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "expense_tracker.db",
    ),
)


# Checked against when an email is unknown, so a failed login takes about as
# long as a wrong password and response time doesn't reveal registered emails.
_DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_hex(16))


class EmailAlreadyRegisteredError(Exception):
    """Raised when a user tries to register with an email already in use."""


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


def get_user_by_email(email):
    """Return the user row for an already-normalised email, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row for the given id, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def authenticate_user(email, password):
    """Return the user row if the password matches, otherwise None.

    Expects an already-normalised email.
    """
    user = get_user_by_email(email)
    if user is None:
        check_password_hash(_DUMMY_PASSWORD_HASH, password)
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def create_user(name, email, password):
    """Insert a user with a hashed password and return the new id.

    The UNIQUE constraint on email is the real guard against duplicates;
    callers may pre-check with get_user_by_email() for a friendly error,
    but two concurrent sign-ups can still race past that check.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        if "users.email" in str(exc):
            raise EmailAlreadyRegisteredError(email) from exc
        raise
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
