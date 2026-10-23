from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id

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


@app.route("/profile")
def profile():
    # Auth guard
    if not session.get("user_id"):
        flash("Please sign in to view your profile", "error")
        return redirect(url_for("login"))

    # Hardcoded demo data for Step 4 (matches seed data in db.py)
    user = {
        "name": session.get("user_name", "Demo User"),
        "email": session.get("user_email", "demo@spendly.com"),
        "member_since": "January 2025"
    }

    stats = {
        "total_expenses": 24,
        "total_spent": 18240.00,
        "avg_per_expense": 760.00,
        "top_category": "Food"
    }

    transactions = [
        {"date": "2025-01-28", "category": "Food", "amount": 450.00, "description": "Weekly groceries"},
        {"date": "2025-01-25", "category": "Transport", "amount": 120.00, "description": "Fuel refill"},
        {"date": "2025-01-22", "category": "Bills", "amount": 2500.00, "description": "Electricity bill"},
        {"date": "2025-01-20", "category": "Health", "amount": 850.00, "description": "Prescription"},
        {"date": "2025-01-18", "category": "Entertainment", "amount": 600.00, "description": "Movie tickets"},
        {"date": "2025-01-15", "category": "Shopping", "amount": 1800.00, "description": "New shirt"},
        {"date": "2025-01-12", "category": "Food", "amount": 320.00, "description": "Coffee and snacks"},
        {"date": "2025-01-10", "category": "Transport", "amount": 80.00, "description": "Bus to work"},
    ]

    category_breakdown = [
        {"category": "Food", "amount": 7800.00, "percentage": 43, "count": 8},
        {"category": "Bills", "amount": 4500.00, "percentage": 25, "count": 2},
        {"category": "Shopping", "amount": 3200.00, "percentage": 18, "count": 3},
        {"category": "Health", "amount": 1200.00, "percentage": 6, "count": 2},
        {"category": "Transport", "amount": 900.00, "percentage": 5, "count": 3},
        {"category": "Entertainment", "amount": 640.00, "percentage": 3, "count": 2},
    ]

    return render_template("profile.html",
                          user=user,
                          stats=stats,
                          transactions=transactions,
                          categories=category_breakdown)


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
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
