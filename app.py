from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id
from database.queries import get_user_by_id as get_user_profile, get_summary_stats, get_recent_transactions, get_category_breakdown

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

    user_id = session["user_id"]

    # Get user info from database
    user = get_user_profile(user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("logout"))

    # Get real data from DB
    stats_raw = get_summary_stats(user_id)
    transactions = get_recent_transactions(user_id, limit=10)
    categories = get_category_breakdown(user_id)

    # Transform stats to match template expectations
    stats = {
        "total_expenses": stats_raw["transaction_count"],
        "total_spent": stats_raw["total_spent"],
        "avg_per_expense": round(stats_raw["total_spent"] / stats_raw["transaction_count"], 2) if stats_raw["transaction_count"] > 0 else 0,
        "top_category": stats_raw["top_category"] or "—"
    }

    return render_template("profile.html",
                          user=user,
                          stats=stats,
                          transactions=transactions,
                          categories=categories)


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
