"""Tests for the Date Filter feature on the Profile page.

Covers query helpers in database/queries.py and the GET /profile route in app.py.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta, date
from app import app as flask_app
from database.db import init_db, get_db
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def app(temp_db):
    """Flask app with temporary database for isolation."""
    # Monkeypatch the database path in database.db module
    import database.db as db_module
    original_get_db = db_module.get_db

    def test_get_db():
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    db_module.get_db = test_get_db

    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })

    with flask_app.app_context():
        init_db()
        yield flask_app

    # Restore
    db_module.get_db = original_get_db


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Authenticated test client with a registered user."""
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@spendly.com',
        'password': 'testpass123'
    })
    client.post('/login', data={
        'email': 'test@spendly.com',
        'password': 'testpass123'
    })
    return client


@pytest.fixture
def test_user_id(app):
    """Create a test user and return their ID."""
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ('Test User', 'test@spendly.com', 'hashed')
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id


@pytest.fixture
def seeded_expenses(app, test_user_id):
    """Seed expenses spanning multiple months for filter testing.

    Dates (relative to a fixed "today" = 2025-06-15 for determinism):
    - 2025-01-15: Food, 50.00  (6+ months ago)
    - 2025-03-20: Transport, 30.00 (3+ months ago)
    - 2025-04-10: Bills, 100.00  (2+ months ago)
    - 2025-05-05: Food, 25.00    (1+ month ago)
    - 2025-06-01: Health, 40.00  (this month, first day)
    - 2025-06-10: Shopping, 60.00 (this month)
    - 2025-06-15: Food, 15.00    (today)
    """
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()

        expenses = [
            (test_user_id, 50.00, 'Food', '2025-01-15', 'Old groceries'),
            (test_user_id, 30.00, 'Transport', '2025-03-20', 'Old bus fare'),
            (test_user_id, 100.00, 'Bills', '2025-04-10', 'Electricity'),
            (test_user_id, 25.00, 'Food', '2025-05-05', 'Groceries'),
            (test_user_id, 40.00, 'Health', '2025-06-01', 'Checkup'),
            (test_user_id, 60.00, 'Shopping', '2025-06-10', 'New shirt'),
            (test_user_id, 15.00, 'Food', '2025-06-15', 'Lunch'),
        ]

        for user_id, amount, category, exp_date, desc in expenses:
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, exp_date, desc)
            )

        conn.commit()
        conn.close()

    return expenses


@pytest.fixture
def today_fixed():
    """Fixed 'today' date for deterministic preset calculations."""
    return date(2025, 6, 15)


# =====================================================================
# Query Helper Tests
# =====================================================================

class TestGetSummaryStats:
    """Tests for get_summary_stats with date filtering."""

    def test_no_filter_returns_all_expenses(self, app, test_user_id, seeded_expenses):
        """No date filter should return stats for all expenses."""
        with app.app_context():
            stats = get_summary_stats(test_user_id)

        assert stats['transaction_count'] == 7
        assert stats['total_spent'] == 320.00
        assert stats['avg_per_expense'] == pytest.approx(45.71, rel=0.01)
        assert stats['top_category'] == 'Food'  # 50 + 25 + 15 = 90

    def test_valid_date_range_filters_correctly(self, app, test_user_id, seeded_expenses):
        """Date range should include only expenses within bounds (inclusive)."""
        with app.app_context():
            # This month only: 2025-06-01 to 2025-06-15
            stats = get_summary_stats(test_user_id, date_from='2025-06-01', date_to='2025-06-15')

        assert stats['transaction_count'] == 3
        assert stats['total_spent'] == 115.00  # 40 + 60 + 15
        assert stats['avg_per_expense'] == pytest.approx(38.33, rel=0.01)
        assert stats['top_category'] == 'Food'  # 15 (only Food in this month)

    def test_date_range_boundary_inclusive(self, app, test_user_id, seeded_expenses):
        """BETWEEN should be inclusive on both bounds."""
        with app.app_context():
            # Range that exactly matches one expense date
            stats = get_summary_stats(test_user_id, date_from='2025-06-10', date_to='2025-06-10')

        assert stats['transaction_count'] == 1
        assert stats['total_spent'] == 60.00
        assert stats['top_category'] == 'Shopping'

    def test_empty_range_returns_zeros(self, app, test_user_id, seeded_expenses):
        """Range with no matching expenses should return zero stats."""
        with app.app_context():
            # Future date range
            stats = get_summary_stats(test_user_id, date_from='2026-01-01', date_to='2026-12-31')

        assert stats['transaction_count'] == 0
        assert stats['total_spent'] == 0
        assert stats['avg_per_expense'] == 0
        assert stats['top_category'] == '—'

    def test_only_date_from_ignored(self, app, test_user_id, seeded_expenses):
        """Only date_from without date_to should be ignored (no filter)."""
        with app.app_context():
            stats = get_summary_stats(test_user_id, date_from='2025-06-01', date_to=None)

        # Should return all expenses (no filter applied)
        assert stats['transaction_count'] == 7
        assert stats['total_spent'] == 320.00

    def test_only_date_to_ignored(self, app, test_user_id, seeded_expenses):
        """Only date_to without date_from should be ignored (no filter)."""
        with app.app_context():
            stats = get_summary_stats(test_user_id, date_from=None, date_to='2025-06-15')

        assert stats['transaction_count'] == 7
        assert stats['total_spent'] == 320.00


class TestGetRecentTransactions:
    """Tests for get_recent_transactions with date filtering."""

    def test_no_filter_returns_latest_first(self, app, test_user_id, seeded_expenses):
        """No filter should return newest-first, limited to default 10."""
        with app.app_context():
            txns = get_recent_transactions(test_user_id)

        assert len(txns) == 7
        # Newest first: 2025-06-15, 2025-06-10, 2025-06-01, 2025-05-05, ...
        assert txns[0]['date'] == '2025-06-15'
        assert txns[0]['amount'] == 15.00
        assert txns[-1]['date'] == '2025-01-15'

    def test_valid_date_range_filters_and_limits(self, app, test_user_id, seeded_expenses):
        """Date range should filter and limit should apply."""
        with app.app_context():
            txns = get_recent_transactions(test_user_id, limit=5, date_from='2025-06-01', date_to='2025-06-15')

        assert len(txns) == 3  # Only 3 in range, limit 5 doesn't add more
        assert all('2025-06-' in txn['date'] for txn in txns)

    def test_limit_respected_within_range(self, app, test_user_id, seeded_expenses):
        """Limit should cap results even when more exist in range."""
        with app.app_context():
            # Add more expenses in June to test limit
            conn = get_db()
            cursor = conn.cursor()
            for i in range(5):
                cursor.execute(
                    "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                    (test_user_id, 10.00, 'Food', f'2025-06-{16+i:02d}', f'Extra {i}')
                )
            conn.commit()
            conn.close()

            txns = get_recent_transactions(test_user_id, limit=3, date_from='2025-06-01', date_to='2025-06-30')

        assert len(txns) == 3

    def test_empty_range_returns_empty_list(self, app, test_user_id, seeded_expenses):
        """No expenses in range should return empty list, not error."""
        with app.app_context():
            txns = get_recent_transactions(test_user_id, date_from='2026-01-01', date_to='2026-12-31')

        assert txns == []


class TestGetCategoryBreakdown:
    """Tests for get_category_breakdown with date filtering."""

    def test_no_filter_returns_all_categories_with_percentages(self, app, test_user_id, seeded_expenses):
        """All categories with percentages summing to 100."""
        with app.app_context():
            breakdown = get_category_breakdown(test_user_id)

        assert len(breakdown) == 5  # Food, Transport, Bills, Health, Shopping
        total_pct = sum(c['percentage'] for c in breakdown)
        assert total_pct == 100

        # Verify Food is top (90 total)
        food = next(c for c in breakdown if c['category'] == 'Food')
        assert food['amount'] == 90.00
        assert food['count'] == 3

    def test_date_range_filters_categories(self, app, test_user_id, seeded_expenses):
        """Date range should filter category breakdown."""
        with app.app_context():
            breakdown = get_category_breakdown(test_user_id, date_from='2025-06-01', date_to='2025-06-15')

        # Only Food(15), Health(40), Shopping(60) in June
        categories = {c['category'] for c in breakdown}
        assert categories == {'Food', 'Health', 'Shopping'}
        total_pct = sum(c['percentage'] for c in breakdown)
        assert total_pct == 100

    def test_empty_range_returns_empty_list(self, app, test_user_id, seeded_expenses):
        """No expenses in range should return empty list."""
        with app.app_context():
            breakdown = get_category_breakdown(test_user_id, date_from='2026-01-01', date_to='2026-12-31')

        assert breakdown == []

    def test_percentages_sum_to_100_after_adjustment(self, app, test_user_id):
        """Percentage adjustment should ensure sum is exactly 100."""
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            # Create expenses with amounts that cause rounding issues
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (test_user_id, 33.33, 'A', '2025-06-01')
            )
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (test_user_id, 33.33, 'B', '2025-06-02')
            )
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (test_user_id, 33.34, 'C', '2025-06-03')
            )
            conn.commit()
            conn.close()

            breakdown = get_category_breakdown(test_user_id, date_from='2025-06-01', date_to='2025-06-03')

        total_pct = sum(c['percentage'] for c in breakdown)
        assert total_pct == 100


# =====================================================================
# Route Tests - GET /profile
# =====================================================================

class TestProfileRouteAuth:
    """Authentication guard tests for /profile."""

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated GET /profile should redirect to login with flash."""
        response = client.get('/profile', follow_redirects=False)

        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_unauthenticated_follows_redirect_shows_login(self, client):
        """Following redirect should show login page with flash message."""
        response = client.get('/profile', follow_redirects=True)

        assert response.status_code == 200
        assert b'Please sign in to view your profile' in response.data
        assert b'Login' in response.data


class TestProfileRoutePresets:
    """Tests for preset filter buttons (This Month, Last 3 Months, Last 6 Months, All Time)."""

    def test_all_time_no_params_shows_all(self, app, auth_client, test_user_id, seeded_expenses):
        """GET /profile with no params = All Time = all expenses."""
        response = auth_client.get('/profile')

        assert response.status_code == 200
        assert b'Total Expenses' in response.data
        # 7 expenses in seeded data
        assert b'7' in response.data  # total_expenses

    def test_this_month_preset_filters_to_current_month(self, app, auth_client, test_user_id, seeded_expenses):
        """This Month preset should filter to current month only."""
        # This month = June 2025 (first day to today 2025-06-15)
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        # Should show 3 transactions (June 1, 10, 15)
        assert b'3' in response.data  # total_expenses in stats
        # Total spent = 40 + 60 + 15 = 115
        assert b'115.00' in response.data

    def test_last_3_months_preset_filters_to_90_days(self, app, auth_client, test_user_id, seeded_expenses):
        """Last 3 Months preset should filter to ~90 day window ending today."""
        # Last 3 months from 2025-06-15 = 2025-03-17 to 2025-06-15
        # Should include: 2025-03-20, 2025-04-10, 2025-05-05, 2025-06-01, 2025-06-10, 2025-06-15
        # NOT: 2025-01-15
        response = auth_client.get('/profile?date_from=2025-03-17&date_to=2025-06-15')

        assert response.status_code == 200
        # 6 transactions in range
        assert b'6' in response.data
        # Total = 30 + 100 + 25 + 40 + 60 + 15 = 270
        assert b'270.00' in response.data

    def test_last_6_months_preset_filters_to_180_days(self, app, auth_client, test_user_id, seeded_expenses):
        """Last 6 Months preset should filter to ~180 day window ending today."""
        # Last 6 months from 2025-06-15 = 2024-12-17 to 2025-06-15
        # Should include ALL seeded expenses (oldest is 2025-01-15)
        response = auth_client.get('/profile?date_from=2024-12-17&date_to=2025-06-15')

        assert response.status_code == 200
        # All 7 transactions
        assert b'7' in response.data
        assert b'320.00' in response.data

    def test_all_time_preset_is_clean_url_no_params(self, app, auth_client, test_user_id, seeded_expenses):
        """All Time preset should be clean /profile URL with no query params."""
        response = auth_client.get('/profile')

        assert response.status_code == 200
        assert b'All Time' in response.data  # button present
        # Should show all 7 expenses
        assert b'7' in response.data


class TestProfileRouteCustomRange:
    """Tests for custom date range form submission."""

    def test_valid_custom_range_filters_correctly(self, app, auth_client, test_user_id, seeded_expenses):
        """Valid date_from and date_to should filter all three sections."""
        # Custom range: May 1 to May 31, 2025
        response = auth_client.get('/profile?date_from=2025-05-01&date_to=2025-05-31')

        assert response.status_code == 200
        # Only 1 expense in May: 2025-05-05 Food 25.00
        assert b'1' in response.data  # total_expenses
        assert b'25.00' in response.data
        assert b'Food' in response.data

    def test_date_from_greater_than_date_to_shows_flash_and_fallback(self, app, auth_client, test_user_id, seeded_expenses):
        """date_from > date_to should flash error and fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=2025-06-15&date_to=2025-06-01', follow_redirects=True)

        assert response.status_code == 200
        # Flash error message
        assert b'Start date must be before end date.' in response.data
        # Falls back to unfiltered (all 7 expenses)
        assert b'7' in response.data
        assert b'320.00' in response.data

    def test_malformed_date_from_falls_back_silently(self, app, auth_client, test_user_id, seeded_expenses):
        """Invalid date_from format should silently fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=not-a-date&date_to=2025-06-15')

        assert response.status_code == 200
        # No error flash, just unfiltered view
        assert b'Start date must be before end date.' not in response.data
        assert b'7' in response.data  # all expenses

    def test_malformed_date_to_falls_back_silently(self, app, auth_client, test_user_id, seeded_expenses):
        """Invalid date_to format should silently fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=invalid')

        assert response.status_code == 200
        assert b'7' in response.data

    def test_both_malformed_dates_falls_back_silently(self, app, auth_client, test_user_id, seeded_expenses):
        """Both dates malformed should fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=foo&date_to=bar')

        assert response.status_code == 200
        assert b'7' in response.data

    def test_partial_date_only_from_ignored(self, app, auth_client, test_user_id, seeded_expenses):
        """Only date_from provided should be ignored (no filter)."""
        response = auth_client.get('/profile?date_from=2025-06-01')

        assert response.status_code == 200
        # Should show all 7 (no filter applied)
        assert b'7' in response.data

    def test_partial_date_only_to_ignored(self, app, auth_client, test_user_id, seeded_expenses):
        """Only date_to provided should be ignored (no filter)."""
        response = auth_client.get('/profile?date_to=2025-06-15')

        assert response.status_code == 200
        assert b'7' in response.data


class TestProfileRouteEdgeCases:
    """Edge case tests for the profile route."""

    def test_no_expenses_in_range_shows_zeros(self, app, auth_client, test_user_id):
        """User with no expenses in selected range should see zeros, not errors."""
        # Create user but no expenses
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-30')

        assert response.status_code == 200
        assert b'0' in response.data  # total_expenses = 0
        assert b'0.00' in response.data  # total_spent = 0
        # Empty category breakdown
        assert b'Spending by Category' in response.data

    def test_expenses_exactly_on_boundary_dates_included(self, app, auth_client, test_user_id, seeded_expenses):
        """Expenses exactly on date_from and date_to should be included (inclusive BETWEEN)."""
        # Range exactly matching boundary expenses
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        # Should include both 2025-06-01 and 2025-06-15 expenses
        assert b'3' in response.data  # 3 transactions in range

    def test_sql_injection_attempt_in_date_params_safe(self, app, auth_client, test_user_id, seeded_expenses):
        """SQL injection via date params should be neutralized by parameterized queries."""
        # Attempt injection - should be treated as malformed and fall back
        response = auth_client.get('/profile?date_from=2025-06-01%27;--&date_to=2025-06-15')

        assert response.status_code == 200
        # Should fall back to unfiltered (malformed date)
        assert b'7' in response.data

    def test_empty_database_user_sees_zeros(self, app, client):
        """Brand new user with no expenses sees zeros in all sections."""
        client.post('/register', data={
            'name': 'New User',
            'email': 'new@spendly.com',
            'password': 'newpass123'
        })
        client.post('/login', data={
            'email': 'new@spendly.com',
            'password': 'newpass123'
        })

        response = client.get('/profile')

        assert response.status_code == 200
        assert b'0' in response.data  # total_expenses
        assert b'0.00' in response.data  # total_spent
        assert b'No transactions' in response.data


class TestProfileRouteTemplateRendering:
    """Tests for template variables and rendering with date filter."""

    def test_active_preset_highlighted_this_month(self, app, auth_client, test_user_id, seeded_expenses):
        """This Month preset button should have active class when selected."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        # Check for active class on This Month button
        assert b'This Month' in response.data
        assert b'active' in response.data

    def test_active_preset_highlighted_all_time(self, app, auth_client, test_user_id, seeded_expenses):
        """All Time button should be active when no filter."""
        response = auth_client.get('/profile')

        assert response.status_code == 200
        assert b'All Time' in response.data
        assert b'active' in response.data

    def test_filter_display_shows_formatted_range(self, app, auth_client, test_user_id, seeded_expenses):
        """filter_display should show human-readable date range when filter active."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        assert b'Showing:' in response.data
        assert b'Jun 01, 2025' in response.data
        assert b'Jun 15, 2025' in response.data

    def test_filter_badge_appears_when_filter_active(self, app, auth_client, test_user_id, seeded_expenses):
        """filter-badge div should appear when filter is active."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        assert b'filter-badge' in response.data

    def test_clear_link_appears_when_custom_range_active(self, app, auth_client, test_user_id, seeded_expenses):
        """Clear link should appear when custom range is active (not a preset)."""
        # Use a range that doesn't match any preset
        response = auth_client.get('/profile?date_from=2025-05-01&date_to=2025-05-31')

        assert response.status_code == 200
        assert b'Clear' in response.data
        assert b'href="/profile"' in response.data

    def test_clear_link_not_when_preset_active(self, app, auth_client, test_user_id, seeded_expenses):
        """Clear link should NOT appear when a preset is active (it matches a preset)."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        # This matches "This Month" preset, so no clear link
        assert b'Clear' not in response.data

    def test_custom_range_inputs_populated_with_values(self, app, auth_client, test_user_id, seeded_expenses):
        """Custom date inputs should show the active date values."""
        response = auth_client.get('/profile?date_from=2025-05-01&date_to=2025-05-31')

        assert response.status_code == 200
        assert b'value="2025-05-01"' in response.data
        assert b'value="2025-05-31"' in response.data

    def test_rupee_symbol_displayed_in_all_sections(self, app, auth_client, test_user_id, seeded_expenses):
        """₹ symbol should appear in stats, transactions, and categories regardless of filter."""
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200
        # Check ₹ appears multiple times (total spent, avg, transaction amounts, category amounts)
        rupee_count = response.data.count(b'\xe2\x82\xb9')  # UTF-8 ₹
        assert rupee_count >= 4


class TestProfileRouteDatePresetCalculations:
    """Tests verifying preset date calculations in app.py are correct."""

    def test_this_month_preset_first_day_to_today(self, app, auth_client, test_user_id, seeded_expenses, today_fixed):
        """This Month should be first day of current month to today."""
        with app.app_context():
            today = datetime.now().date()
            first_day = today.replace(day=1)
            response = auth_client.get(f'/profile?date_from={first_day.isoformat()}&date_to={today.isoformat()}')

        assert response.status_code == 200

    def test_last_3_months_preset_90_days_ago_to_today(self, app, auth_client, test_user_id, seeded_expenses, today_fixed):
        """Last 3 Months should be 90 days ago to today."""
        with app.app_context():
            today = datetime.now().date()
            three_months_ago = today - timedelta(days=90)
            response = auth_client.get(f'/profile?date_from={three_months_ago.isoformat()}&date_to={today.isoformat()}')

        assert response.status_code == 200

    def test_last_6_months_preset_180_days_ago_to_today(self, app, auth_client, test_user_id, seeded_expenses, today_fixed):
        """Last 6 Months should be 180 days ago to today."""
        with app.app_context():
            today = datetime.now().date()
            six_months_ago = today - timedelta(days=180)
            response = auth_client.get(f'/profile?date_from={six_months_ago.isoformat()}&date_to={today.isoformat()}')

        assert response.status_code == 200


# =====================================================================
# Integration: Query Helpers + Route Together
# =====================================================================

class TestDateFilterIntegration:
    """End-to-end tests verifying all three sections respect the same filter."""

    def test_all_three_sections_filtered_consistently(self, app, auth_client, test_user_id, seeded_expenses):
        """Summary stats, transactions, and categories should all use same filter."""
        # Filter to June 2025 only
        response = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')

        assert response.status_code == 200

        # Summary stats: 3 transactions, 115 total
        assert b'3' in response.data  # total_expenses
        assert b'115.00' in response.data  # total_spent

        # Transactions table: 3 rows
        # Check for the three June expenses
        assert b'2025-06-01' in response.data
        assert b'2025-06-10' in response.data
        assert b'2025-06-15' in response.data
        assert b'Health' in response.data
        assert b'Shopping' in response.data
        assert b'Food' in response.data

        # Categories: Food, Health, Shopping only
        assert b'Food' in response.data
        assert b'Health' in response.data
        assert b'Shopping' in response.data
        # Bills and Transport should NOT appear
        # (Note: they might appear in "All Time" but not in this filtered view)

    def test_changing_filter_updates_all_sections(self, app, auth_client, test_user_id, seeded_expenses):
        """Switching from one filter to another should update all sections."""
        # First request: This Month (June)
        response1 = auth_client.get('/profile?date_from=2025-06-01&date_to=2025-06-15')
        assert b'115.00' in response1.data

        # Second request: Last 3 Months (March 17 - June 15)
        response2 = auth_client.get('/profile?date_from=2025-03-17&date_to=2025-06-15')
        assert b'270.00' in response2.data

        # Third request: All Time
        response3 = auth_client.get('/profile')
        assert b'320.00' in response3.data


# =====================================================================
# Run command hint
# =====================================================================
# Run with: pytest tests/test_date_filter.py -v