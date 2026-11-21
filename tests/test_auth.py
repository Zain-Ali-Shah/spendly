import re

import pytest

import database.db as db

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"
LOGIN_ERROR = b"Invalid email or password."


def post_login(client, **overrides):
    data = {"email": DEMO_EMAIL, "password": DEMO_PASSWORD, **overrides}
    return client.post("/login", data=data)


def session_user_id(client):
    with client.session_transaction() as sess:
        return sess.get("user_id")


def test_get_login_renders_form(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b'action="/login"' in response.data


def test_login_success_redirects_and_sets_session(client):
    response = post_login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert session_user_id(client) == db.get_user_by_email(DEMO_EMAIL)["id"]


def test_navbar_shows_user_after_login(client):
    response = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Demo User" in response.data
    assert b"Sign out" in response.data
    assert b"Welcome back, Demo User." in response.data
    assert b"Get started" not in response.data


@pytest.mark.parametrize("email", ["DEMO@Spendly.com", "  demo@spendly.com  "])
def test_login_email_is_normalized(client, email):
    response = post_login(client, email=email)

    assert response.status_code == 302
    assert session_user_id(client) is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "wrong-password"},
        {"email": "nobody@example.com"},
        {"email": ""},
        {"password": ""},
        {"email": "", "password": ""},
    ],
)
def test_login_failure_is_generic(client, overrides):
    response = post_login(client, **overrides)

    assert response.status_code == 401
    assert LOGIN_ERROR in response.data
    assert session_user_id(client) is None


def test_failed_login_keeps_email_not_password(client):
    response = post_login(client, password="wrong-password")

    assert response.status_code == 401
    assert b'value="demo@spendly.com"' in response.data
    assert b"wrong-password" not in response.data
    password_input = re.search(rb'<input type="password"[^>]*>', response.data)
    assert password_input is not None
    assert b"value=" not in password_input.group(0)


def test_registered_user_can_log_in(client):
    client.post(
        "/register",
        data={
            "name": "Ayesha Khan",
            "email": "ayesha@example.com",
            "password": "strongpass1",
        },
    )

    response = post_login(client, email="ayesha@example.com", password="strongpass1")

    assert response.status_code == 302
    assert session_user_id(client) == db.get_user_by_email("ayesha@example.com")["id"]


def test_logout_clears_session(client):
    post_login(client)

    response = client.post("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/login"
    assert b"You have been signed out." in response.data
    assert b"Get started" in response.data
    assert session_user_id(client) is None


def test_logout_when_signed_out_redirects_to_login(client):
    response = client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_get_logout_not_allowed(client):
    post_login(client)

    response = client.get("/logout")

    assert response.status_code == 405
    assert session_user_id(client) is not None


@pytest.mark.parametrize("path", ["/login", "/register"])
def test_signed_in_user_redirected_from_auth_pages(client, path):
    post_login(client)

    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_stale_session_treated_as_signed_out(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 999999

    response = client.get("/")

    assert response.status_code == 200
    assert b"Sign out" not in response.data
    assert b"Get started" in response.data
    assert session_user_id(client) is None


def test_session_cookie_flags(client):
    response = post_login(client)

    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_authenticate_user(app):
    user = db.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD)

    assert user is not None
    assert user["email"] == DEMO_EMAIL
    assert db.authenticate_user(DEMO_EMAIL, "wrong-password") is None
    assert db.authenticate_user("nobody@example.com", DEMO_PASSWORD) is None


def test_get_user_by_id(app):
    demo = db.get_user_by_email(DEMO_EMAIL)

    assert db.get_user_by_id(demo["id"])["email"] == DEMO_EMAIL
    assert db.get_user_by_id(999999) is None
