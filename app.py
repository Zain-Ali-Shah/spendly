import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    create_user,
    get_db,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
# The fallback exists only so local development works without setup;
# any shared or deployed instance must set SECRET_KEY.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

with app.app_context():
    init_db()
    seed_db()

NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists."
LOGIN_ERROR_MESSAGE = "Invalid email or password."
SIGN_IN_REQUIRED_MESSAGE = "Please sign in to view your profile."

# Placeholder data so the profile page can be designed before real stats exist.
# It mirrors the seeded demo expenses; Step 5 replaces it with database/db.py
# queries scoped to the signed-in user.
PLACEHOLDER_TRANSACTIONS = [
    {"date": date, "description": description, "category": category,
     "amount": amount}
    for date, description, category, amount in [
        ("2026-11-22", "Dinner out", "Food", 950.00),
        ("2026-11-18", "Miscellaneous", "Other", 700.00),
        ("2026-11-15", "Clothes", "Shopping", 4500.00),
        ("2026-11-12", "Cinema tickets", "Entertainment", 2000.00),
        ("2026-11-09", "Pharmacy", "Health", 1500.00),
        ("2026-11-06", "Electricity bill", "Bills", 6500.00),
        ("2026-11-04", "Fuel", "Transport", 800.00),
        ("2026-11-02", "Groceries", "Food", 1250.00),
    ]
]
PLACEHOLDER_CATEGORIES = [
    {"name": "Bills", "amount": 6500.00},
    {"name": "Shopping", "amount": 4500.00},
    {"name": "Food", "amount": 2200.00},
    {"name": "Entertainment", "amount": 2000.00},
    {"name": "Health", "amount": 1500.00},
    {"name": "Transport", "amount": 800.00},
    {"name": "Other", "amount": 700.00},
]
PLACEHOLDER_SUMMARY = {"total": 18200.00, "count": 8, "top_category": "Bills"}


def validate_registration(name, email, password):
    """Return the first validation error message, or None if input is valid.

    Expects name and email already stripped and email already lowercased.
    """
    if not name:
        return "Please enter your name."
    if len(name) > NAME_MAX_LENGTH:
        return f"Name must be at most {NAME_MAX_LENGTH} characters."

    local, _, domain = email.partition("@")
    if not local or not domain:
        return "Please enter a valid email address."
    if len(email) > EMAIL_MAX_LENGTH:
        return f"Email must be at most {EMAIL_MAX_LENGTH} characters."

    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters."

    return None


def _parse_date(value):
    """Parse the leading YYYY-MM-DD of a stored date, or return None."""
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


@app.template_filter("month_year")
def month_year(value):
    """'2026-11-26 10:15:00' -> 'November 2026'; '' if unparseable."""
    parsed = _parse_date(value)
    return parsed.strftime("%B %Y") if parsed else ""


@app.template_filter("short_date")
def short_date(value):
    """'2026-11-02' -> '02 Nov 2026'; '' if unparseable."""
    parsed = _parse_date(value)
    return parsed.strftime("%d %b %Y") if parsed else ""


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash(SIGN_IN_REQUIRED_MESSAGE, "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def load_current_user():
    g.user = None
    if request.endpoint == "static":
        return
    user_id = session.get("user_id")
    if user_id is None:
        return
    g.user = get_user_by_id(user_id)
    if g.user is None:
        session.clear()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = validate_registration(name, email, password)
    if error is None and get_user_by_email(email) is not None:
        error = DUPLICATE_EMAIL_MESSAGE

    if error is None:
        try:
            create_user(name, email, password)
        except EmailAlreadyRegisteredError:
            error = DUPLICATE_EMAIL_MESSAGE

    if error is not None:
        return (
            render_template("register.html", error=error, name=name, email=email),
            400,
        )

    flash("Account created. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = authenticate_user(email, password) if email and password else None
    if user is None:
        return (
            render_template("login.html", error=LOGIN_ERROR_MESSAGE, email=email),
            401,
        )

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
        user=g.user,
        summary=PLACEHOLDER_SUMMARY,
        transactions=PLACEHOLDER_TRANSACTIONS,
        categories=PLACEHOLDER_CATEGORIES,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
