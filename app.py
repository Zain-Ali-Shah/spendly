import os

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
        return redirect(url_for("landing"))

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
        return redirect(url_for("landing"))

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
    flash(f"Welcome back, {user['name']}.", "success")
    return redirect(url_for("landing"))


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


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
