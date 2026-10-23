import sqlite3
import os
from werkzeug.security import generate_password_hash


def get_db():
    """Returns a SQLite connection with row_factory set and foreign keys enabled."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def init_db():
    """Creates all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def create_user(name: str, email: str, password: str) -> int | None:
    """
    Create a new user with hashed password.
    Returns user_id on success, None if email already exists.
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Email already exists (UNIQUE constraint)
        return None
    finally:
        conn.close()


def seed_db():
    """Inserts demo data if users table is empty."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if users table already has data
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        return

    # Create demo user
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123"))
    )
    user_id = cursor.lastrowid

    # Current month dates
    from datetime import datetime
    today = datetime.now()
    dates = [
        f"{today.year}-{today.month:02d}-15",
        f"{today.year}-{today.month:02d}-18",
        f"{today.year}-{today.month:02d}-20",
        f"{today.year}-{today.month:02d}-22",
        f"{today.year}-{today.month:02d}-25",
        f"{today.year}-{today.month:02d}-28",
        f"{today.year}-{today.month:02d}-30",
        f"{today.year}-{today.month:02d}-01"
    ]

    # Insert sample expenses
    expenses = [
        (20.50, "Food", "Weekly groceries", dates[0]),
        (5.00, "Transport", "Bus to work", dates[1]),
        (80.00, "Bills", "Electricity bill", dates[2]),
        (25.00, "Health", "Prescription", dates[3]),
        (15.00, "Entertainment", "Movie tickets", dates[4]),
        (45.00, "Shopping", "New shirt", dates[5]),
        (10.00, "Food", "Coffee and snacks", dates[6]),
        (30.00, "Transport", "Fuel refill", dates[7])
    ]

    for amount, category, description, date in expenses:
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description)
        )

    conn.commit()
    conn.close()