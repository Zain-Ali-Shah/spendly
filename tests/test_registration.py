import os
import re

import pytest

import database.db as db

VALID_FORM = {
    "name": "Ayesha Khan",
    "email": "ayesha@example.com",
    "password": "strongpass1",
}

PROJECT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)


def post_register(client, **overrides):
    return client.post("/register", data={**VALID_FORM, **overrides})


def test_real_db_untouched():
    assert os.path.abspath(db.DB_PATH) != os.path.abspath(PROJECT_DB)


def test_get_register_renders_form(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b'action="/register"' in response.data


def test_register_success_redirects_to_login(client, user_count):
    before = user_count()

    response = post_register(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert user_count() == before + 1


def test_success_flash_shown_on_login(client):
    response = client.post("/register", data=VALID_FORM, follow_redirects=True)

    assert response.status_code == 200
    assert b"Account created" in response.data
    assert b"auth-success" in response.data


def test_password_is_hashed(client):
    post_register(client)

    user = db.get_user_by_email(VALID_FORM["email"])
    assert user["password_hash"] != VALID_FORM["password"]
    assert user["password_hash"].startswith("scrypt:")


def test_email_normalized(client):
    post_register(client, email="  New@Example.COM ")

    assert db.get_user_by_email("new@example.com") is not None


@pytest.mark.parametrize("email", ["demo@spendly.com", "DEMO@spendly.com"])
def test_duplicate_email_rejected(client, user_count, email):
    before = user_count()

    response = post_register(client, email=email)

    assert response.status_code == 400
    assert b"An account with this email already exists" in response.data
    assert user_count() == before


def test_create_user_raises_on_duplicate(app):
    with pytest.raises(db.EmailAlreadyRegisteredError):
        db.create_user("Someone", "demo@spendly.com", "whatever123")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": ""}, b"Please enter your name."),
        ({"name": "   "}, b"Please enter your name."),
        ({"name": "a" * 101}, b"Name must be at most 100 characters."),
        ({"email": ""}, b"Please enter a valid email address."),
        ({"email": "not-an-email"}, b"Please enter a valid email address."),
        ({"email": "@example.com"}, b"Please enter a valid email address."),
        ({"email": "user@"}, b"Please enter a valid email address."),
        ({"email": "a" * 250 + "@x.com"}, b"Email must be at most 254 characters."),
        ({"password": ""}, b"Password must be at least 8 characters."),
        ({"password": "short77"}, b"Password must be at least 8 characters."),
        ({"password": "p" * 129}, b"Password must be at most 128 characters."),
    ],
)
def test_invalid_input_rejected(client, user_count, overrides, message):
    before = user_count()

    response = post_register(client, **overrides)

    assert response.status_code == 400
    assert message in response.data
    assert user_count() == before


def test_failed_submit_keeps_name_email_not_password(client):
    response = post_register(client, password="short77")

    assert response.status_code == 400
    assert b'value="Ayesha Khan"' in response.data
    assert b'value="ayesha@example.com"' in response.data
    assert b"short77" not in response.data
    password_input = re.search(rb'<input type="password"[^>]*>', response.data)
    assert password_input is not None
    assert b"value=" not in password_input.group(0)


def test_refresh_after_success_does_not_duplicate(client, user_count):
    post_register(client)
    after_first = user_count()

    response = post_register(client)

    assert response.status_code == 400
    assert user_count() == after_first
