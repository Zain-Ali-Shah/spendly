import os
import tempfile

# app.py runs init_db()/seed_db() at import time, so the database path must
# be redirected before anything imports it, or the real database gets touched.
os.environ["SPENDLY_DB_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="spendly-test-"), "import.db"
)

import pytest  # noqa: E402

import database.db as db  # noqa: E402
from app import app as flask_app  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def user_count():
    def count():
        conn = db.get_db()
        try:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()

    return count
