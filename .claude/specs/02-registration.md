# Spec: Registration

## Overview

Make the existing registration page work. Today `GET /register` only renders
`register.html`, and the form posts to a route that does not accept `POST`.
This step adds `POST /register` so a visitor can create an account: the form
input is validated, the password is hashed with werkzeug, and a row is inserted
into the `users` table created in Step 1. After a successful sign-up the user
is redirected to the login page with a success message. Logging in itself is
not part of this step — Step 3 (login/logout) builds on the accounts created
here.

## Depends on

- **Step 1 — Database setup**: `get_db()`, `init_db()` and the `users` table
  (`name`, `email UNIQUE`, `password_hash`) in `database/db.py`.

## Routes

- `GET /register` — render the registration form (already exists, now shares a
  view function with POST) — public
- `POST /register` — validate input, create the user, redirect to
  `url_for('login')` with a flash message; on invalid input re-render
  `register.html` with an error and status `400` — public

No other routes change. `/logout`, `/profile` and the expense routes stay stubs.

## Database changes

No database changes. The `users` table in `database/db.py` already has every
column and constraint this step needs:

- `email TEXT UNIQUE NOT NULL` — enforces one account per email at the DB level
- `password_hash TEXT NOT NULL`

New helpers in `database/db.py` (DB logic stays out of `app.py`):

- `get_user_by_email(email)` — returns a `sqlite3.Row` or `None`
- `create_user(name, email, password)` — hashes the password with
  `werkzeug.security.generate_password_hash`, inserts the row, commits, and
  returns the new user id. It catches `sqlite3.IntegrityError` from the UNIQUE
  constraint and raises a domain error (e.g. `EmailAlreadyRegisteredError`
  defined in `db.py`), so a race between two sign-ups with the same email is
  handled the same way as the friendly pre-check.

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html`
    - change `action="/register"` to `action="{{ url_for('register') }}"`
      (no hardcoded URLs)
    - re-fill `name` and `email` from the submitted values after a failed
      submit (`value="{{ name or '' }}"`); never re-fill the password
    - add `minlength="8"` on the password input to match server-side validation
    - fix the garbled em dash in the `title` block if the file isn't saved
      as UTF-8
  - `templates/login.html` — show flashed messages (the "Account created"
    success message) above the login card, using `get_flashed_messages()`
    if `base.html` doesn't already render them

## Files to change

- `app.py` — `register()` accepts `GET` and `POST`; set `app.secret_key`
  from the `SECRET_KEY` environment variable (needed for `flash()`), with a
  dev-only fallback that is clearly labeled as such
- `database/db.py` — add `get_user_by_email()`, `create_user()` and the
  `EmailAlreadyRegisteredError` exception
- `templates/register.html` — see Templates
- `templates/login.html` — see Templates
- `static/css/style.css` — style for a flash/success message (e.g.
  `.auth-success`) using existing variables (`--accent`, `--accent-light`),
  only if no suitable class exists
- `CLAUDE.md` — update the route table: `POST /register` implemented

## Files to create

- `tests/conftest.py` — app fixture that points `DB_PATH` at a temp file per
  test, so tests never touch `expense_tracker.db`
- `tests/test_registration.py` — tests for the Definition of done below

## New dependencies

No new dependencies. Uses `flask`, `werkzeug` and `pytest` / `pytest-flask`,
which are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders), never f-strings in SQL
- Passwords hashed with werkzeug (`generate_password_hash`, default scrypt
  method); never store or log the plain password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` only; `register()` parses the form,
  calls the helper, and renders or redirects
- Use `url_for()` for every internal link and form action
- Validation, done on the server whatever the browser checks:
  - `name`: required, stripped, 1–100 characters
  - `email`: required, stripped and lowercased before lookup and insert, must
    contain `@`, at most 254 characters
  - `password`: required, at least 8 characters, at most 128
- Duplicate email returns a generic message ("An account with this email
  already exists") and status `400` — no stack trace
- Successful POST uses redirect-after-POST (`302` to `/login`) so a refresh
  doesn't resubmit
- Do not log the user in automatically — session handling is Step 3
- Do not implement `/logout`, `/profile` or any expense stub

## Definition of done

- [x] `python app.py` starts on port 5001 without errors
- [x] `GET /register` shows the form, and its action is rendered via `url_for`
- [x] Submitting valid name, email and 8+ character password creates a row in
      `users` and redirects to `/login`
- [x] The login page shows an "Account created" success message after that
      redirect
- [x] The stored `password_hash` is a werkzeug hash (starts with `scrypt:`),
      not the plain password
- [x] Registering an email that already exists (including different case,
      e.g. `DEMO@spendly.com`) shows an error, returns 400, and adds no row
- [x] Empty name, invalid email, or a password under 8 characters each show
      an error, return 400, and add no row
- [x] After a failed submit the name and email fields keep their values and
      the password field is empty
- [x] Refreshing the page after a successful sign-up doesn't create a second
      account
- [x] `pytest` passes, and the tests use a temp database, not
      `expense_tracker.db`
