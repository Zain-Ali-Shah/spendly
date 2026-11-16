# Plan: Step 1 — Database setup

## Context
`database/db.py` is an empty stub, so Spendly has no data layer. Spec `.claude/specs/01-database-setup.md` asks for a SQLite layer: `get_db()`, `init_db()`, `seed_db()`, wired into `app.py` at startup. This is the foundation for later steps (register, login, profile, expenses). No new routes; stub routes stay untouched.

Only `database/db.py` and `app.py` change. (`database/__init__.py` already exists.)

## 1. `database/db.py`
Imports: `os`, `sqlite3`, `date` from datetime, `generate_password_hash` from `werkzeug.security`.

- `DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db")` — project root, independent of CWD; name already in `.gitignore`. Read at call time (so tests can monkeypatch).
- `get_db()`: `sqlite3.connect(DB_PATH)`, `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON` on every connection, return connection (caller closes).
- `init_db()`: `executescript` with `CREATE TABLE IF NOT EXISTS` for:
  - `users`: id INTEGER PK AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now'))
  - `expenses`: id INTEGER PK AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL (YYYY-MM-DD), description TEXT, created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (user_id) REFERENCES users(id)
  - Close connection in `try/finally`.
- `seed_db()`: return early if `SELECT COUNT(*) FROM users` > 0. Otherwise, in one transaction with parameterized queries:
  - Insert demo user: "Demo User", `demo@spendly.com`, `generate_password_hash("demo123")`; use `lastrowid`.
  - `executemany` insert 8 expenses (amounts in **PKR**, no `$`), dates from `date.today().replace(day=N)` with N ≤ 28:

    | Day | Category | Amount | Description |
    |---|---|---|---|
    | 2 | Food | 1250.00 | Groceries |
    | 4 | Transport | 800.00 | Fuel |
    | 6 | Bills | 6500.00 | Electricity bill |
    | 9 | Health | 1500.00 | Pharmacy |
    | 12 | Entertainment | 2000.00 | Cinema tickets |
    | 15 | Shopping | 4500.00 | Clothes |
    | 18 | Other | 700.00 | Miscellaneous |
    | 22 | Food | 950.00 | Dinner out |
  - `commit()`, close in `finally`.

## 2. `app.py`
- Add `from database.db import get_db, init_db, seed_db` (`get_db` unused for now, per spec; needed by step 2).
- Right after `app = Flask(__name__)`:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```
  Module-level so `flask run` and tests also create the DB. Runs twice under the debug reloader; safe because both functions are idempotent.
- Leave routes, stub strings, and `app.run(debug=True, port=5001)` unchanged.

## Edge cases / notes
- FK enforcement works only because the PRAGMA is set per connection in `get_db()`.
- A stale old `expense_tracker.db` won't be migrated by `IF NOT EXISTS`; delete it manually if present (gitignored).
- Spec typos (garbled werkzeug import, mailto-formatted email) resolved to normal code/plain address.
- `.claude/plans/` is gitignored, so this plan file won't be committed.

## Verification
1. Smoke test from project root: run `init_db(); seed_db()` twice via `python -c`, then confirm 1 user, 8 expenses, all 7 categories, `PRAGMA foreign_keys` = 1, and `expense_tracker.db` is created but not shown in `git status`.
2. `python app.py` starts on port 5001; `/`, `/login`, `/register` return 200; restart adds no duplicate rows.
3. `check_password_hash(hash, "demo123")` is True and the stored hash isn't plaintext.
4. Optional (beyond spec) `tests/test_database.py`, monkeypatching `database.db.DB_PATH` to `tmp_path`: schema/columns, idempotent init and seed, 1 user + 8 expenses + all categories + current-month dates, FK violation and duplicate email raise `sqlite3.IntegrityError`, `row_factory is sqlite3.Row`. Keep tests off `import app` (it would seed the real DB).
5. Per CLAUDE.md, after implementation use a subagent to verify test results.
