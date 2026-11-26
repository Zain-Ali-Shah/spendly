# Spec: Profile Page Design

## Overview

Replace the `GET /profile` stub (it returns a raw string) with a real, signed-in
profile page. The point of this step is the **design and layout**: a user info
card, a row of summary stat tiles, a recent-transactions table and a
spending-by-category breakdown, all in PKR. The user's own details (name, email,
member-since date) come from `g.user`, which Step 3 already loads on every
request. The spending figures are **placeholder data** defined in `app.py` and
shaped like the real data, so the template can be built and reviewed now. Step 5
will swap them for real queries against the `expenses` table without changing
the template. This is also the first protected page, so it adds the
`login_required` guard. Sign-in now lands on `/profile` instead of `/`, as Step 3
planned.

## Depends on

- **Step 1 — Database setup**: `users` table (`id`, `name`, `email`,
  `created_at`) and the seeded demo user.
- **Step 2 — Registration**: real user accounts.
- **Step 3 — Login and Logout**: `session["user_id"]`, the `before_request`
  hook that sets `g.user`, flash rendering in `base.html`, and the signed-in
  navbar.

## Routes

- `GET /profile` — render `profile.html` for the signed-in user, built from
  `g.user` plus the placeholder summary, transactions and categories. If no one
  is signed in, flash "Please sign in to view your profile." and redirect
  (`302`) to `url_for('login')`. Access: logged-in.
- `POST /login` (changed): on success, redirect to `url_for('profile')`
  instead of `url_for('landing')`. Access: public.
- `GET /login` and `GET /register` (changed): if someone is already signed
  in, redirect to `url_for('profile')` instead of `url_for('landing')`.
  Access: public.

No `?next=` parameter yet. After sign-in the user always lands on `/profile`,
so there is no open-redirect handling to get wrong.

## Database changes

No database changes and no new `database/db.py` helpers. `g.user` already holds
the whole `users` row. Real expense queries belong to Step 5.

## Templates

- **Create:**
  - `templates/profile.html`: extends `base.html`, loads
    `css/profile.css` through `{% block head %}`, and sets
    `{% block title %}Profile · Spendly{% endblock %}`. Sections:
    1. **User card**: an avatar circle with the user's initials (worked out in
       the template from `user['name']`), the name, the email, and
       "Member since <Month YYYY>" from `user['created_at']`.
    2. **Summary stats**: three tiles: *Total spent* (`Rs 18,200.00`),
       *Transactions* (`8`) and *Top category* (`Bills`).
    3. **Recent transactions**: a table with Date, Description, Category (as
       a badge) and Amount (right-aligned, `Rs` prefix, two decimals). If the
       list is empty, show an empty state instead of the table.
    4. **Spending by category**: one row per category with its name, amount
       and a horizontal bar whose width is its percentage of the total
       (inline `style="width: N%"` set from data is allowed; colours are not).
  - Every amount is formatted as `Rs {{ "{:,.2f}".format(amount) }}`. Never
    use `$` or USD.
- **Modify:**
  - `templates/base.html`: when signed in, add a "Profile" nav link
    (`url_for('profile')`) before the user's name.

## Files to change

- `app.py`
  - add a `login_required` decorator (built with `functools.wraps`) that
    checks `g.user`, flashes the sign-in message and redirects to `login`
  - replace the `profile()` stub. It is decorated with `@login_required` and
    renders `profile.html` with `user=g.user, summary=..., transactions=...,
    categories=...`
  - add module-level placeholder constants (`PLACEHOLDER_SUMMARY`,
    `PLACEHOLDER_TRANSACTIONS`, `PLACEHOLDER_CATEGORIES`) with a comment
    saying Step 5 replaces them with `database/db.py` queries. Their values
    mirror the seeded demo data (8 expenses, Rs 18,200 total) so the page looks
    plausible, and they use the fixed category list from Step 1
  - `login()` and `register()` redirect to `profile` (see Routes)
- `templates/base.html`: see Templates
- `tests/test_auth.py`: update the assertions that expect a redirect to `/`
  after login, or for signed-in users on `/login` and `/register`, so they
  expect `/profile`
- `CLAUDE.md`: route table: `GET /profile` becomes "Implemented — renders
  `profile.html` (placeholder stats until Step 5)"

## Files to create

- `templates/profile.html`
- `static/css/profile.css`: profile-only styles (cards, stat grid, table,
  badges, category bars). It uses only variables from `style.css` `:root`
  (`--paper-card`, `--border`, `--accent`, `--accent-light`, `--accent-2`,
  `--ink-*`, `--radius-*`, `--font-*`). It is responsive: stat tiles stack in
  one column and the table scrolls inside its card below about 640px, with no
  horizontal page scroll.
- `tests/test_profile.py`: tests for the Definition of done below, using
  the existing `app` fixture in `tests/conftest.py` (temp database)

## New dependencies

No new dependencies. No icon library or CDN script. Use text, CSS or inline
SVG if an icon is needed.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (none are added in this step)
- Passwords hashed with werkzeug (not touched in this step)
- Use CSS variables and never hardcode hex values. If a colour is missing, add a
  token to `:root` in `style.css`
- All templates extend `base.html`
- `url_for()` for every internal link and form action
- No inline `<style>` tags. Page styles go in `static/css/profile.css`
- Identity comes only from `g.user` (the signed session). `/profile` takes
  no user id from the URL, query string or form
- Route function stays thin: guard, gather context, render
- No DB logic in `app.py`. The placeholder data is plain Python constants, not
  queries
- Currency is PKR (`Rs`) everywhere and never `$`
- Rely on Jinja autoescaping for the user's name and email. Never use `|safe`
- Do not implement the expense stubs (Steps 7–9) or real stats (Step 5)

## Definition of done

- [ ] `python app.py` starts on port 5001 without errors
- [ ] Signed out, `GET /profile` redirects to `/login` and shows "Please sign
      in to view your profile."
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/profile`
- [ ] The profile page shows "Demo User", `demo@spendly.com`, initials "DU"
      and a "Member since" month and year
- [ ] The stat tiles show `Rs 18,200.00`, `8` and `Bills`
- [ ] The transactions table lists the placeholder rows with `Rs` amounts to
      two decimals, and no `$` appears anywhere on the page
- [ ] Category bars show and their widths reflect each category's share
- [ ] A newly registered user who signs in sees their own name and email on
      `/profile`, not the demo user's
- [ ] The navbar shows a "Profile" link when signed in and hides it when
      signed out
- [ ] Visiting `/login` or `/register` while signed in redirects to `/profile`
- [ ] At phone width (about 375px) the page has no horizontal scroll and the
      stat tiles stack
- [ ] `profile.css` contains no hex colour values, and `profile.html` has no
      `<style>` tag and no hardcoded internal URLs
- [ ] `pytest` passes: the existing registration and auth tests (updated for
      the new redirect target) plus the new `tests/test_profile.py`
