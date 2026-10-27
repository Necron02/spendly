# Spec: Edit Expense

## Overview
This feature implements the expense editing flow, allowing logged-in users to modify their existing expenses. It is Step 8 in the Spendly roadmap and depends on the authentication system (Steps 2-3), the expenses table schema (Step 1), and the add-expense feature (Step 7). The feature adds a GET route to display the pre-filled edit form and a POST route to process updates, with server-side validation, authorization checks (users can only edit their own expenses), and user-friendly error handling.

## Depends on
- Step 1: Database Setup (expenses table exists with user_id foreign key)
- Step 2: Registration (users can create accounts)
- Step 3: Login and Logout (users can authenticate and maintain sessions)
- Step 7: Add Expense (validation logic, categories, form structure already established)

## Routes
- `GET /expenses/<int:id>/edit` — Display the edit expense form pre-filled with existing data — logged-in only, owner only
- `POST /expenses/<int:id>/edit` — Process form submission, validate, update DB, redirect to profile — logged-in only, owner only

## Database changes
No database changes. The `expenses` table already exists with columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

New query functions needed in `database/queries.py`:
- `get_expense_by_id(user_id: int, expense_id: int) -> dict | None` — Fetch expense by ID for authorization and pre-filling form
- `update_expense(user_id: int, expense_id: int, amount: float, category: str, date: str, description: str | None) -> bool` — Update expense record, returns True on success

## Templates
- **Create:** `templates/edit_expense.html` — Form for editing an existing expense (similar to add_expense.html but pre-filled)
- **Modify:** `templates/profile.html` — Add "Edit" button/link in the transactions table for each expense row, linking to `url_for('edit_expense', id=txn.id)`

## Files to change
- `app.py` — Implement GET and POST route handlers for `/expenses/<int:id>/edit`
- `database/queries.py` — Add `get_expense_by_id()` and `update_expense()` functions
- `templates/profile.html` — Add edit button in transaction table rows

## Files to create
- `templates/edit_expense.html` — New template extending `base.html` with pre-filled expense form

## New dependencies
No new dependencies. Uses existing: Flask, Werkzeug, SQLite3.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries
- Parameterized queries only — never use f-strings in SQL
- All templates must extend `base.html`
- Use CSS variables — never hardcode hex values in templates or new CSS
- Route functions: one responsibility — fetch/validate data, render template, done
- DB logic belongs in `database/queries.py`, never inline in routes
- Use `abort(404)` if expense not found, `abort(403)` if user tries to edit another user's expense
- Form validation: same rules as add expense (amount required, positive number; category required from predefined list; date required, not in future; description optional, max 500 chars)
- Category values must match existing categories: Food, Transport, Bills, Health, Entertainment, Shopping (case-sensitive)
- On validation error, re-render form with error messages and preserve user input
- On success, flash success message and redirect to `/profile`
- Pre-fill form with existing expense data on GET request
- Unauthenticated users redirected to `/login` with flash message
- Users can only edit their own expenses (verify `expense.user_id == session["user_id"]`)

## Definition of done
- [ ] `GET /expenses/<id>/edit` renders the edit expense form pre-filled with existing expense data
- [ ] Form uses `url_for('edit_expense', id=expense.id)` for action
- [ ] Category dropdown includes all 6 seeded categories with current category selected
- [ ] Date field shows existing date, max value is today (no future dates)
- [ ] Description field shows existing description (or empty if none)
- [ ] `POST /expenses/<id>/edit` validates all fields server-side
- [ ] Validation errors show inline with preserved form data
- [ ] Valid submission updates record in `expenses` table
- [ ] On success, flashes "Expense updated successfully" and redirects to `/profile`
- [ ] Updated expense appears immediately in profile transaction list and stats update
- [ ] Unauthenticated users redirected to `/login` with flash message
- [ ] Users cannot edit other users' expenses (returns 403 or redirects with error)
- [ ] Non-existent expense IDs return 404
- [ ] Edit button appears in profile transaction table for each expense
- [ ] All templates extend `base.html` and use CSS variables
- [ ] No raw SQL in route handlers — all DB logic in `database/queries.py`