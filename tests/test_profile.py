import re
from pathlib import Path

import pytest

import database.db as db
from app import (
    PLACEHOLDER_CATEGORIES,
    PLACEHOLDER_SUMMARY,
    PLACEHOLDER_TRANSACTIONS,
    month_year,
    short_date,
)

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"
SIGN_IN_MESSAGE = b"Please sign in to view your profile."
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def post_login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def register_and_login(client, name, email, password="s3cure-pass"):
    client.post(
        "/register", data={"name": name, "email": email, "password": password}
    )
    post_login(client, email=email, password=password)


def rupees(amount):
    return f"Rs {amount:,.2f}".encode()


# ------------------------------------------------------------------ #
# Access                                                              #
# ------------------------------------------------------------------ #

def test_profile_requires_login(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_redirect_shows_sign_in_message(client):
    response = client.get("/profile", follow_redirects=True)

    assert response.request.path == "/login"
    assert SIGN_IN_MESSAGE in response.data


def test_stale_session_cannot_view_profile(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 999999

    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_lands_on_profile(client):
    response = post_login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


# ------------------------------------------------------------------ #
# Content                                                             #
# ------------------------------------------------------------------ #

def test_profile_shows_user_details(client):
    post_login(client)

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"Demo User" in response.data
    assert DEMO_EMAIL.encode() in response.data
    assert b">DU<" in response.data
    created_at = db.get_user_by_email(DEMO_EMAIL)["created_at"]
    assert f"Member since {month_year(created_at)}".encode() in response.data


def test_profile_shows_summary_stats(client):
    post_login(client)

    response = client.get("/profile")

    assert response.status_code == 200
    assert b'class="profile-stat-value">Rs 18,200.00<' in response.data
    assert b'class="profile-stat-value">8<' in response.data
    assert b'class="profile-stat-value">Bills<' in response.data


def test_profile_lists_transactions_in_pkr(client):
    post_login(client)

    response = client.get("/profile")

    assert response.status_code == 200
    for transaction in PLACEHOLDER_TRANSACTIONS:
        assert transaction["description"].encode() in response.data
        assert rupees(transaction["amount"]) in response.data
    assert b"$" not in response.data


def test_profile_category_bars_reflect_share(client):
    post_login(client)

    response = client.get("/profile")

    total = PLACEHOLDER_SUMMARY["total"]
    for category in PLACEHOLDER_CATEGORIES:
        share = round(category["amount"] / total * 100, 1)
        assert f"width: {share}%".encode() in response.data
    # Bills is 6,500 of 18,200.
    assert b"width: 35.7%" in response.data


def test_profile_shows_only_own_details(client):
    register_and_login(client, "Ayesha Khan", "ayesha@example.com")

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"Ayesha Khan" in response.data
    assert b"ayesha@example.com" in response.data
    assert b">AK<" in response.data
    assert b"Demo User" not in response.data
    assert DEMO_EMAIL.encode() not in response.data


def test_profile_ignores_user_id_in_query(client):
    register_and_login(client, "Ayesha Khan", "ayesha@example.com")

    response = client.get("/profile?user_id=1")

    assert b"Ayesha Khan" in response.data
    assert DEMO_EMAIL.encode() not in response.data


def test_navbar_profile_link_only_when_signed_in(client):
    signed_out = client.get("/")
    post_login(client)
    signed_in = client.get("/")

    assert b">Profile</a>" not in signed_out.data
    assert b'href="/profile" class="nav-profile">Profile</a>' in signed_in.data


# ------------------------------------------------------------------ #
# Filters                                                             #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-26 10:15:00", "November 2026"),
        ("2025-01-03", "January 2025"),
        (None, ""),
        ("", ""),
        ("not a date", ""),
    ],
)
def test_month_year(value, expected):
    assert month_year(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2026-11-02", "02 Nov 2026"), (None, ""), ("bad", "")],
)
def test_short_date(value, expected):
    assert short_date(value) == expected


# ------------------------------------------------------------------ #
# Placeholder data and static rules                                   #
# ------------------------------------------------------------------ #

def test_placeholder_data_is_consistent():
    transaction_total = sum(t["amount"] for t in PLACEHOLDER_TRANSACTIONS)
    category_total = sum(c["amount"] for c in PLACEHOLDER_CATEGORIES)
    largest = max(PLACEHOLDER_CATEGORIES, key=lambda c: c["amount"])

    assert transaction_total == category_total == PLACEHOLDER_SUMMARY["total"]
    assert PLACEHOLDER_SUMMARY["count"] == len(PLACEHOLDER_TRANSACTIONS)
    assert PLACEHOLDER_SUMMARY["top_category"] == largest["name"]


def test_profile_css_has_no_hex_colours():
    css = (PROJECT_ROOT / "static" / "css" / "profile.css").read_text(
        encoding="utf-8"
    )

    assert re.search(r"#[0-9a-fA-F]{3,8}\b", css) is None


def test_profile_template_has_no_inline_styles_or_hardcoded_urls():
    html = (PROJECT_ROOT / "templates" / "profile.html").read_text(
        encoding="utf-8"
    )

    assert "<style" not in html
    for attribute in ("href", "src", "action"):
        assert f'{attribute}="/' not in html
    assert "|safe" not in html
