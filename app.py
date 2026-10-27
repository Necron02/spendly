from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id
from database.queries import get_user_by_id as get_user_profile, get_summary_stats, get_recent_transactions, get_category_breakdown, add_expense as add_expense_db, get_expense_by_id, update_expense, delete_expense as delete_expense_db
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-production"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register")
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_post():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    # Server-side validation
    if not name or not email or not password:
        flash("All fields are required", "error")
        return render_template("register.html", error="All fields are required")

    if len(password) < 8:
        flash("Password must be at least 8 characters", "error")
        return render_template("register.html", error="Password must be at least 8 characters")

    # Attempt to create user
    user_id = create_user(name, email, password)

    if user_id is None:
        flash("Email already registered", "error")
        return render_template("register.html", error="Email already registered")

    flash("Account created successfully! Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/analytics")
def analytics():
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to view analytics", "error")
        return redirect(url_for("login"))

    return render_template("analytics.html")


@app.route("/profile")
def profile():
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to view your profile", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get user info from database
    user = get_user_profile(user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("logout"))

    # Read and validate date filter params
    date_from_str = request.args.get("date_from", "").strip()
    date_to_str = request.args.get("date_to", "").strip()

    date_from = None
    date_to = None
    active_preset = None

    # Validate date_from
    if date_from_str:
        try:
            datetime.strptime(date_from_str, "%Y-%m-%d")
            date_from = date_from_str
        except ValueError:
            pass  # Invalid format - ignore

    # Validate date_to
    if date_to_str:
        try:
            datetime.strptime(date_to_str, "%Y-%m-%d")
            date_to = date_to_str
        except ValueError:
            pass  # Invalid format - ignore

    # Check if date_from > date_to
    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to = None

    # Compute preset date ranges
    today = datetime.now().date()
    presets = {
        "this_month": {
            "label": "This Month",
            "date_from": today.replace(day=1).isoformat(),
            "date_to": today.isoformat()
        },
        "last_3_months": {
            "label": "Last 3 Months",
            "date_from": (today - timedelta(days=90)).isoformat(),
            "date_to": today.isoformat()
        },
        "last_6_months": {
            "label": "Last 6 Months",
            "date_from": (today - timedelta(days=180)).isoformat(),
            "date_to": today.isoformat()
        }
    }

    # Determine active preset
    if date_from and date_to:
        for key, preset in presets.items():
            if preset["date_from"] == date_from and preset["date_to"] == date_to:
                active_preset = key
                break

    # Get real data from DB with date filter
    stats_raw = get_summary_stats(user_id, date_from, date_to)
    transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from, date_to)

    # Transform stats to match template expectations
    stats = {
        "total_expenses": stats_raw["transaction_count"],
        "total_spent": stats_raw["total_spent"],
        "avg_per_expense": round(stats_raw["avg_per_expense"], 2) if stats_raw["transaction_count"] > 0 else 0,
        "top_category": stats_raw["top_category"] or "—"
    }

    # Format filter display
    filter_display = None
    if date_from and date_to:
        try:
            from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            filter_display = f"Showing: {from_dt.strftime('%b %d, %Y')} – {to_dt.strftime('%b %d, %Y')}"
        except Exception:
            filter_display = "Filtered"

    return render_template("profile.html",
                          user=user,
                          stats=stats,
                          transactions=transactions,
                          categories=categories,
                          date_from=date_from,
                          date_to=date_to,
                          active_preset=active_preset,
                          filter_display=filter_display,
                          presets=presets)


ALLOWED_CATEGORIES = {"Food", "Transport", "Bills", "Health", "Entertainment", "Shopping"}


def _validate_expense_form(form) -> dict:
    """Validate expense form data. Returns dict of errors (empty if valid)."""
    errors = {}

    # Amount validation
    amount_str = form.get("amount", "").strip()
    if not amount_str:
        errors["amount"] = "Amount is required"
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors["amount"] = "Amount must be greater than 0"
        except ValueError:
            errors["amount"] = "Invalid amount"

    # Category validation
    category = form.get("category", "").strip()
    if not category:
        errors["category"] = "Category is required"
    elif category not in ALLOWED_CATEGORIES:
        errors["category"] = "Invalid category"

    # Date validation
    date_str = form.get("date", "").strip()
    if not date_str:
        errors["date"] = "Date is required"
    else:
        try:
            from datetime import date as date_cls
            expense_date = date_cls.fromisoformat(date_str)
            today = date_cls.today()
            if expense_date > today:
                errors["date"] = "Date cannot be in the future"
        except ValueError:
            errors["date"] = "Invalid date format"

    # Description validation
    description = form.get("description", "").strip()
    if description and len(description) > 500:
        errors["description"] = "Description must be 500 characters or less"

    return errors


@app.route("/expenses/add")
def add_expense():
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to add an expense", "error")
        return redirect(url_for("login"))

    today = date.today().isoformat()
    return render_template("add_expense.html", today=today)


@app.route("/expenses/add", methods=["POST"])
def add_expense_post():
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to add an expense", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = date.today().isoformat()

    # Validate form
    errors = _validate_expense_form(request.form)
    if errors:
        for field, msg in errors.items():
            flash(msg, "error")
        return render_template("add_expense.html", today=today, errors=errors), 400

    # Extract validated data
    amount = float(request.form["amount"].strip())
    category = request.form["category"].strip()
    expense_date = request.form["date"].strip()
    description = request.form["description"].strip() or None

    # Insert into database
    expense_id = add_expense_db(user_id, amount, category, expense_date, description)

    if expense_id is None:
        flash("Failed to add expense. Please try again.", "error")
        return render_template("add_expense.html", today=today), 500

    flash("Expense added successfully", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to edit an expense", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch expense (with ownership check)
    expense = get_expense_by_id(user_id, id)
    if not expense:
        abort(404)

    today = date.today().isoformat()
    return render_template("edit_expense.html", expense=expense, today=today)


@app.route("/expenses/<int:id>/edit", methods=["POST"])
def edit_expense_post(id):
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to edit an expense", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch expense (with ownership check)
    expense = get_expense_by_id(user_id, id)
    if not expense:
        abort(404)

    # Validate form
    errors = _validate_expense_form(request.form)
    if errors:
        for field, msg in errors.items():
            flash(msg, "error")
        return render_template("edit_expense.html", expense=expense, today=date.today().isoformat(), errors=errors), 400

    # Extract validated data
    amount = float(request.form["amount"].strip())
    category = request.form["category"].strip()
    expense_date = request.form["date"].strip()
    description = request.form["description"].strip() or None

    # Update in database
    success = update_expense(user_id, id, amount, category, expense_date, description)

    if not success:
        flash("Failed to update expense. Please try again.", "error")
        return render_template("edit_expense.html", expense=expense, today=date.today().isoformat()), 500

    flash("Expense updated successfully", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to delete an expense", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch expense (with ownership check)
    expense = get_expense_by_id(user_id, id)
    if not expense:
        abort(404)

    # Delete the expense
    success = delete_expense_db(user_id, id)

    if not success:
        flash("Failed to delete expense. Please try again.", "error")
        return redirect(url_for("profile"))

    flash("Expense deleted successfully", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
