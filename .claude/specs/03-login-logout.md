# Spec: Login and Logout

## Overview

Implement user login and logout functionality for the Spendly expense tracker. This step completes the authentication flow by adding the POST `/login` route to verify credentials and create a session, and the GET `/logout` route to destroy the session. This establishes the session management pattern required for all subsequent protected routes (profile, expenses).

## Depends on

- Step 01 (Database Setup) — requires the `users` table and `get_db()` helper
- Step 02 (Registration) — requires `create_user()` and registration flow to exist

## Routes

- `POST /login` — Process login form, verify credentials, create session, redirect to profile — public access
- `GET /logout` — Destroy session, redirect to landing page — logged-in access
- `GET /login` — Already implemented (renders `login.html`) — public access

## Database changes

No database changes required. The existing `users` table has all necessary columns:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

Sessions will be managed using Flask's built-in `session` object (signed cookies, server-side secret).

## Templates

- **Modify:** `templates/login.html` — Add server-side validation error display (template already has `{% if error %}` block)
- **Modify:** `templates/base.html` — Update navigation to show user state (login/register links when logged out, profile/logout when logged in)

## Files to change

- `app.py` — Add POST `/login` and GET `/logout` route handlers, import `check_password_hash`, `session`
- `database/db.py` — Add `get_user_by_email(email)` helper function
- `templates/login.html` — Ensure error display works (already has the block)
- `templates/base.html` — Conditional navigation based on session state

## Files to create

None

## New dependencies

No new dependencies. Use existing:
- `sqlite3` (standard library)
- `werkzeug.security.check_password_hash` (already in requirements.txt)
- `flask.session` (built into Flask)

## Rules for implementation

- No ORMs (no SQLAlchemy)
- Parameterized queries only — never use f-strings or string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values in templates
- All templates extend `base.html`
- Use Flask's `session` for authentication state (signed cookies)
- Set `app.secret_key` for session signing (already present)
- On invalid credentials, show user-friendly error on the login page (not a 500 error)
- On successful login, redirect to `/profile` (will be implemented in Step 4)
- On logout, clear session and redirect to `/` (landing page)
- Route function: one responsibility — fetch/process data, render template or redirect, done
- DB logic belongs in `database/db.py`, never inline in routes

## Definition of done

- [ ]  GET `/login` renders login form (already working)
- [ ]  POST `/login` accepts form data (email, password)
- [ ]  Valid credentials create session and redirect to `/profile`
- [ ]  Invalid credentials show error message on login page
- [ ]  GET `/logout` clears session and redirects to `/`
- [ ]  Navigation in `base.html` shows "Sign in / Get started" when logged out
- [ ]  Navigation in `base.html` shows user name / "Profile / Logout" when logged in
- [ ]  Password verified using `werkzeug.security.check_password_hash`
- [ ]  All SQL uses parameterized queries (`?` placeholders)
- [ ]  No raw string returns — always render template or redirect
- [ ]  App starts without errors
- [ ]  Can log in with demo user (demo@spendly.com / demo123)
- [ ]  Can log out and return to landing page