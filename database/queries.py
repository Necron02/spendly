"""Database query helpers for the profile page.

Pure functions with no Flask dependencies. Each function opens its own
connection via get_db() and closes it before returning.
"""

from database.db import get_db
from datetime import datetime


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


def get_summary_stats(user_id: int) -> dict:
    """Get total spent, transaction count, top category, and average per expense.

    Returns dict with: total_spent, transaction_count, avg_per_expense, top_category
    """
    conn = get_db()
    cursor = conn.cursor()

    # Total spent and count
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_spent, COUNT(*) as transaction_count
        FROM expenses WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    total_spent = row["total_spent"] or 0
    transaction_count = row["transaction_count"] or 0

    # Top category (highest total amount)
    cursor.execute("""
        SELECT category, SUM(amount) as cat_total
        FROM expenses WHERE user_id = ?
        GROUP BY category ORDER BY cat_total DESC LIMIT 1
    """, (user_id,))
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


def get_recent_transactions(user_id: int, limit: int = 10, offset: int = 0) -> list:
    """Get recent transactions newest-first with pagination.

    Returns list of dicts with: date, category, description, amount
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, category, description, amount
        FROM expenses WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset))
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions


def get_category_breakdown(user_id: int) -> list:
    """Get category breakdown with percentages summing to 100.

    Returns list of dicts with: category, amount, percentage, count
    Percentages are integers that sum to exactly 100.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, SUM(amount) as amount, COUNT(*) as count
        FROM expenses WHERE user_id = ?
        GROUP BY category ORDER BY amount DESC
    """, (user_id,))
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