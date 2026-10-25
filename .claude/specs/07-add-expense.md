# Spec: Add Expense

## Overview
This feature implements the expense creation flow, allowing logged-in users to record new expenses with amount, category, date, and optional description. It is Step 7 in the Spendly roadmap and depends on the authentication system (Steps 2-3) and the existing expenses table schema (Step 1). The feature adds a GET route to display the form and a POST route to process submissions, with server-side validation and user-friendly error handling.

## Depends on
- Step 1: Database Setup (expenses table exists)
- Step 2: Registration (users can create accounts)
- Step 3: Login and Logout (users can authenticate and maintain sessions)

## Routes
- `GET /expenses/add` — Display the add expense form — logged-in only
- `POST /expenses/add` — Process form submission, validate, insert into DB, redirect to profile — logged-in only

## Database changes
No database changes. The `expenses` table already exists with columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates
- **Create:** `templates/add_expense.html` — Form for entering a new expense
- **Modify:** `templates/base.html` — No changes needed (navigation already handles logged-in state)
- **Modify:** `templates/profile.html` — The "Add Expense" button already links to `url_for('add_expense')`

## Files to change
- `app.py` — Add GET and POST route handlers for `/expenses/add`
- `database/queries.py` — Add `add_expense()` function to insert new expense records
- `templates/profile.html` — No changes (button already points to correct route)

## Files to create
- `templates/add_expense.html` — New template extending `base.html` with expense form

## New dependencies
No new dependencies. Uses existing: Flask, Werkzeug (for password hashing, not needed here), SQLite3.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries
- Parameterized queries only — never use f-strings in SQL
- All templates must extend `base.html`
- Use CSS variables — never hardcode hex values in templates or new CSS
- Route functions: one responsibility — fetch/validate data, render template, done
- DB logic belongs in `database/queries.py` (or `database/db.py` for helpers), never inline in routes
- Use `abort()` for HTTP errors (401, 403, 404), not bare string returns
- Form validation: amount required, positive number; category required from predefined list; date required, not in future; description optional, max 500 chars
- Category values must match existing categories in seed data: Food, Transport, Bills, Health, Entertainment, Shopping (case-sensitive)
- On validation error, re-render form with error messages and preserve user input
- On success, flash success message and redirect to `/profile`

## Definition of done
- [ ] `GET /expenses/add` renders the add expense form with all fields (amount, category dropdown, date, description)
- [ ] Form uses `url_for('add_expense')` for action
- [ ] Category dropdown includes all 6 seeded categories: Food, Transport, Bills, Health, Entertainment, Shopping
- [ ] Date field defaults to today, max value is today (no future dates)
- [ ] `POST /expenses/add` validates all fields server-side
- [ ] Validation errors show inline with preserved form data
- [ ] Valid submission inserts record into `expenses` table with correct `user_id` from session
- [ ] On success, flashes "Expense added successfully" and redirects to `/profile`
- [ ] New expense appears immediately in profile transaction list and stats update
- [ ] Unauthenticated users redirected to `/login` with flash message
- [ ] All templates extend `base.html` and use CSS variables
- [ ] No raw SQL in route handlers — all DB logic in `database/queries.py`