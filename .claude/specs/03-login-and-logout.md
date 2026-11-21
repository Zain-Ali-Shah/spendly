# Spec: Login and Logout

## Overview

Make sign-in and sign-out work. Today `GET /login` only renders `login.html`,
its form posts to a hardcoded `/login` that does not accept `POST`, and
`/logout` is a stub that returns a raw string. This step adds `POST /login`,
which checks the email and password against the `users` table from Step 1
(accounts created in Step 2) and starts a Flask server-signed session, and a
real logout that clears it. The navbar switches between "Sign in / Get
started" and the signed-in user's name with a "Sign out" button. This is the
foundation the profile page (Step 4) and all expense routes (Steps 7–9) need
to know who the current user is.

## Depends on

- **Step 1 — Database setup**: `get_db()` and the `users` table
  (`id`, `name`, `email UNIQUE`, `password_hash`).
- **Step 2 — Registration**: `get_user_by_email()`, werkzeug-hashed passwords,
  `app.secret_key` from `SECRET_KEY`, and the flash-message rendering already
  in `login.html`.

## Routes

- `GET /login` — render the sign-in form (already exists, now shares a view
  function with POST); if already signed in, redirect to `url_for('landing')`
  — public
- `POST /login` — normalise email (strip + lowercase), verify credentials,
  on success clear the session, store `user_id`, flash "Welcome back, <name>."
  and redirect (`302`) to `url_for('landing')`; on failure re-render
  `login.html` with a generic error and status `401` — public
- `POST /logout` — clear the session, flash "You have been signed out." and
  redirect (`302`) to `url_for('login')` — logged-in (a signed-out request
  just redirects to login too)
- `GET /register` — additionally redirect to `url_for('landing')` when
  already signed in — public

**Deviation from the CLAUDE.md route table:** logout becomes `POST /logout`
(not `GET`) so a third-party page or an `<img src>` can't sign the user out.
`GET /logout` returns `405`. Update the table in `CLAUDE.md` accordingly.

`/profile` and the expense routes stay stubs. Post-login goes to the landing
page until Step 4 builds `/profile`. No `?next=` redirect parameter in this
step (avoids open-redirect handling until there are protected pages).

## Database changes

No database changes. The `users` table already has every column needed.

New helpers in `database/db.py` (DB and password logic stays out of `app.py`):

- `get_user_by_id(user_id)` — returns a `sqlite3.Row` or `None`
- `authenticate_user(email, password)` — looks up the already-normalised
  email; returns the user row if `werkzeug.security.check_password_hash`
  matches, else `None`. When no user exists for the email, still run
  `check_password_hash` against a fixed dummy hash so response time doesn't
  reveal which emails are registered.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html`
    - change `action="/login"` to `action="{{ url_for('login') }}"`
    - re-fill the `email` field after a failed submit
      (`value="{{ email or '' }}"`); never re-fill the password
    - replace the placeholder `nitish@example.com` with a neutral one
      (e.g. `you@example.com`)
  - `templates/base.html`
    - when `g.user` is set: show the user's name and a "Sign out" button inside
      a `<form method="POST" action="{{ url_for('logout') }}">`; hide
      "Sign in" / "Get started"
    - when not signed in: keep the current links
    - render flashed messages on pages other than login (e.g. the "Welcome
      back" message on landing) — move flash rendering into `base.html` once
      and remove the duplicate loop from `login.html` so messages don't show
      twice
    - fix the hardcoded `/terms` and `/privacy` footer links to `url_for()`

## Files to change

- `app.py`
  - `login()` accepts `GET` and `POST`
  - `logout()` becomes `POST`-only, renders nothing, redirects
  - `register()` redirects signed-in users away
  - a `@app.before_request` hook loads `g.user = get_user_by_id(session["user_id"])`
    when a `user_id` is in the session; if the row no longer exists, clear the
    session and leave `g.user = None`
  - set `SESSION_COOKIE_HTTPONLY=True` (Flask default, make explicit) and
    `SESSION_COOKIE_SAMESITE="Lax"`
- `database/db.py` — add `get_user_by_id()` and `authenticate_user()`
- `templates/login.html` — see Templates
- `templates/base.html` — see Templates
- `static/css/style.css` — styles for the nav user name and the sign-out
  button (styled like a nav link) using existing variables, only if no
  suitable class exists
- `CLAUDE.md` — route table: `POST /login` and `POST /logout` implemented;
  helper list in Warnings gains `get_user_by_id`, `authenticate_user`

## Files to create

- `tests/test_auth.py` — tests for the Definition of done below, using the
  existing `app` fixture in `tests/conftest.py` (temp database)

## New dependencies

No new dependencies. Uses `flask`, `werkzeug`, `pytest` and `pytest-flask`,
already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders), never f-strings in SQL
- Passwords verified with werkzeug `check_password_hash`; never log, flash,
  or re-render the plain password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `url_for()` for every internal link and form action
- DB logic lives in `database/db.py` only; route functions parse input, call a
  helper, then render or redirect
- Identity comes only from the signed session cookie (`session["user_id"]`),
  never from a form field or query parameter
- Call `session.clear()` before setting `user_id` on login (prevents session
  fixation) and on logout
- Failed login always shows the same message — "Invalid email or password." —
  for unknown email, wrong password, or empty fields, with status `401`
- Do not enforce the registration password length rules on login: the seeded
  demo account's password (`demo123`) is 7 characters
- Successful login and logout use redirect-after-POST
- Do not implement `/profile` or any expense stub; no `login_required`
  decorator yet (nothing to protect until Step 4)

## Definition of done

- [ ] `python app.py` starts on port 5001 without errors
- [ ] `GET /login` shows the form; its action is rendered via `url_for`
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/` and the
      navbar shows "Demo User" and a "Sign out" button instead of
      "Sign in / Get started"
- [ ] Email is case-insensitive: `DEMO@Spendly.com` / `demo123` also signs in
- [ ] A wrong password, an unknown email, and empty fields each show
      "Invalid email or password.", return `401`, and leave no `user_id` in the
      session
- [ ] After a failed submit the email field keeps its value and the password
      field is empty
- [ ] A user registered via `/register` can then sign in with those details
- [ ] Clicking "Sign out" clears the session, redirects to `/login` with a
      "signed out" message, and the navbar shows "Sign in / Get started" again
- [ ] `GET /logout` returns `405` and does not sign the user out
- [ ] Visiting `/login` or `/register` while signed in redirects to `/`
- [ ] A session whose `user_id` no longer exists in `users` is treated as
      signed out (no error)
- [ ] The session cookie is `HttpOnly` and `SameSite=Lax`
- [ ] `pytest` passes (existing registration tests plus new `tests/test_auth.py`),
      using a temp database, not `expense_tracker.db`
