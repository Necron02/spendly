"""Database query helpers for the profile page.

Pure functions with no Flask dependencies. Each function opens its own
connection via get_db() and closes it before returning.
"""

from database.db import get_db
from datetime import datetime
from typing import Optional
import sqlite3


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID with formatted member_since.

    Returns dict with: name, email, member_since (formatted as "Month YYYY")
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Parse created_at and format as "Month YYYY"
        created = user["created_at"]
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            member_since = dt.strftime("%B %Y")
        except Exception:
            member_since = "Unknown"
        return {
            "name": user["name"],
            "email": user["email"],
            "member_since": member_since
        }
    return None


def _build_date_filter(date_from: Optional[str], date_to: Optional[str]) -> tuple[str, list]:
    """Build WHERE clause fragment and parameters for date range filter.

    Returns (where_fragment, params) where where_fragment is empty string if no filter.
    """
    if date_from and date_to:
        return "AND date BETWEEN ? AND ?", [date_from, date_to]
    return "", []


def get_summary_stats(user_id: int, date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """Get total spent, transaction count, top category, and average per expense.

    Returns dict with: total_spent, transaction_count, avg_per_expense, top_category
    """
    conn = get_db()
    cursor = conn.cursor()

    date_where, date_params = _build_date_filter(date_from, date_to)
    base_params = [user_id] + date_params

    # Total spent and count
    cursor.execute(f"""
        SELECT COALESCE(SUM(amount), 0) as total_spent, COUNT(*) as transaction_count
        FROM expenses WHERE user_id = ? {date_where}
    """, base_params)
    row = cursor.fetchone()
    total_spent = row["total_spent"] or 0
    transaction_count = row["transaction_count"] or 0

    # Top category (highest total amount)
    cursor.execute(f"""
        SELECT category, SUM(amount) as cat_total
        FROM expenses WHERE user_id = ? {date_where}
        GROUP BY category ORDER BY cat_total DESC LIMIT 1
    """, base_params)
    top_row = cursor.fetchone()
    top_category = top_row["category"] if top_row else "—"

    avg_per_expense = total_spent / transaction_count if transaction_count > 0 else 0

    conn.close()
    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "avg_per_expense": avg_per_expense,
        "top_category": top_category
    }


def get_recent_transactions(user_id: int, limit: int = 10, date_from: Optional[str] = None, date_to: Optional[str] = None) -> list:
    """Get recent transactions newest-first with optional date filter.

    Returns list of dicts with: id, date, category, description, amount
    """
    conn = get_db()
    cursor = conn.cursor()

    date_where, date_params = _build_date_filter(date_from, date_to)
    base_params = [user_id] + date_params + [limit]

    cursor.execute(f"""
        SELECT id, date, category, description, amount
        FROM expenses WHERE user_id = ? {date_where}
        ORDER BY date DESC, id DESC
        LIMIT ?
    """, base_params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions


def get_category_breakdown(user_id: int, date_from: Optional[str] = None, date_to: Optional[str] = None) -> list:
    """Get category breakdown with percentages summing to 100.

    Returns list of dicts with: category, amount, percentage, count
    Percentages are integers that sum to exactly 100.
    """
    conn = get_db()
    cursor = conn.cursor()

    date_where, date_params = _build_date_filter(date_from, date_to)
    base_params = [user_id] + date_params

    cursor.execute(f"""
        SELECT category, SUM(amount) as amount, COUNT(*) as count
        FROM expenses WHERE user_id = ? {date_where}
        GROUP BY category ORDER BY amount DESC
    """, base_params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    total = sum(row["amount"] for row in rows)
    breakdown = []
    for row in rows:
        pct = round((row["amount"] / total) * 100) if total > 0 else 0
        breakdown.append({
            "category": row["category"],
            "amount": row["amount"],
            "percentage": pct,
            "count": row["count"]
        })

    # Adjust largest category to make percentages sum to 100
    pct_sum = sum(c["percentage"] for c in breakdown)
    if pct_sum != 100 and breakdown:
        diff = 100 - pct_sum
        breakdown[0]["percentage"] += diff

    return breakdown


def add_expense(user_id: int, amount: float, category: str, date: str, description: str | None = None) -> int | None:
    """Insert a new expense record.

    Returns the new expense id on success, None on failure.
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def get_expense_by_id(user_id: int, expense_id: int) -> dict | None:
    """Get expense by ID for a specific user.

    Returns dict with: id, user_id, amount, category, date, description, created_at
    Returns None if not found or doesn't belong to user.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    expense = cursor.fetchone()
    conn.close()

    if expense:
        return dict(expense)
    return None


def update_expense(user_id: int, expense_id: int, amount: float, category: str, date: str, description: str | None = None) -> bool:
    """Update an expense record.

    Returns True on success, False on failure or if expense doesn't belong to user.
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def delete_expense(user_id: int, expense_id: int) -> bool:
    """Delete an expense record.

    Returns True on success, False if expense doesn't belong to user or not found.
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()