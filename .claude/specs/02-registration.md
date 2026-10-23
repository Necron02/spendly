# Spec: Registration

## Overview

Implement the POST `/register` endpoint to handle user registration. This step completes the registration flow by processing the form submission from the existing `register.html` template, creating a new user account with hashed password, and redirecting to the login page on success with a success message. This is the first authentication feature and establishes the pattern for all future auth flows.

## Depends on

- Step 01 (Database Setup) — requires the `users` table and `get_db()` helper to be functional

## Routes

- `POST /register` — Process registration form, create user, redirect to login — public access
- `GET /register` — Already implemented (renders `register.html`) — public access

## Database changes

No database changes required. The `users` table already exists with the necessary columns:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

## Templates

- **Modify:** `templates/register.html` — Add server-side validation error display (template already has `{% if error %}` block, just needs to be populated from route)

## Files to change

- `app.py` — Add POST `/register` route handler
- `database/db.py` — Add `create_user(name, email, password)` helper function
- `templates/register.html` — Ensure error display works (already has the block)

## Files to create

None

## New dependencies

No new dependencies. Use existing:
- `sqlite3` (standard library)
- `werkzeug.security.generate_password_hash` (already in requirements.txt)

## Rules for implementation

- No ORMs (no SQLAlchemy)
- Parameterized queries only — never use f-strings or string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values in templates
- All templates extend `base.html`
- On duplicate email, show user-friendly error on the registration page (not a 500 error)
- On success, redirect to `/login` with a flash message or query param indicating success
- Route function: one responsibility — fetch/process data, render template or redirect, done
- DB logic belongs in `database/db.py`, never inline in routes

## Definition of done

- [ ]  GET `/register` renders registration form (already working)
- [ ]  POST `/register` accepts form data (name, email, password)
- [ ]  Valid submission creates user in database with hashed password
- [ ]  Duplicate email shows error message on registration page
- [ ]  Successful registration redirects to `/login`
- [ ]  Password is hashed using `werkzeug.security.generate_password_hash`
- [ ]  All SQL uses parameterized queries (`?` placeholders)
- [ ]  No raw string returns — always render template or redirect
- [ ]  App starts without errors
- [ ]  Can register a new user and see them in the database