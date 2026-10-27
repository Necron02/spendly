import pytest
from datetime import date, timedelta


class TestEditExpenseGet:
    """Test GET /expenses/<id>/edit route."""

    def test_redirect_unauthenticated_user(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/expenses/1/edit")
        assert response.status_code == 302
        assert response.location == "/login"

    def test_render_form_for_existing_expense(self, client, auth):
        """Authenticated user should see pre-filled edit form."""
        # Login first
        auth.login()
        response = client.get("/expenses/1/edit")
        assert response.status_code == 200
        assert b"Edit Expense" in response.data
        assert b"Update Expense" in response.data
        # Check pre-filled data
        assert b"value=\"20.5\"" in response.data  # original amount
        assert b"selected>Food" in response.data  # category
        assert b"value=\"2026-10-15\"" in response.data  # date
        assert b"Weekly groceries" in response.data  # description

    def test_return_404_nonexistent_expense(self, client, auth):
        """Non-existent expense ID should return 404."""
        auth.login()
        response = client.get("/expenses/9999/edit")
        assert response.status_code == 404

    def test_return_403_other_user_expense(self, client, auth, new_user):
        """Cannot edit another user's expense."""
        auth.register(new_user["email"], new_user["password"], "Another User")
        auth.login()
        response = client.get("/expenses/1/edit")  # expense belongs to demo user
        assert response.status_code == 404  # expense not found for this user


class TestEditExpensePost:
    """Test POST /expenses/<id>/edit route."""

    def test_redirect_unauthenticated_user(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.post("/expenses/1/edit", data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-10-15",
            "description": "test"
        })
        assert response.status_code == 302
        assert response.location == "/login"

    def test_validate_required_fields(self, client, auth):
        """Missing required fields should show validation errors."""
        auth.login()
        response = client.post("/expenses/1/edit", data={
            "amount": "",
            "category": "",
            "date": "",
            "description": ""
        })
        assert response.status_code == 400
        assert b"All fields required" in response.data  # flash message

    def test_validate_amount_positive(self, client, auth):
        """Negative or zero amount should show error."""
        auth.login()
        # Zero amount error
        response = client.post("/expenses/1/edit", data={
            "amount": "0.00",
            "category": "Food",
            "date": "2026-10-15",
            "description": ""
        })
        assert response.status_code == 400
        assert b"Amount must be greater than 0" in response.data

        # Negative amount error
        response = client.post("/expenses/1/edit", data={
            "amount": "-5",
            "category": "Food",
            "date": "2026-10-15",
            "description": ""
        })
        assert response.status_code == 400
        assert b"Amount must be greater than 0" in response.data

    def test_validate_category_valid_options(self, client, auth):
        """Invalid category should show error."""
        auth.login()
        response = client.post("/expenses/1/edit", data={
            "amount": "25.00",
            "category": "InvalidCategory",
            "date": "2026-10-15",
            "description": ""
        })
        assert response.status_code == 400
        assert b"Invalid category" in response.data

    def test_validate_date_not_future(self, client, auth):
        """Date cannot be in the future."""
        future_date = (date.today() + timedelta(days=1)).isoformat()
        auth.login()
        response = client.post("/expenses/1/edit", data={
            "amount": "25.00",
            "category": "Food",
            "date": future_date,
            "description": ""
        })
        assert response.status_code == 400
        assert b"Date cannot be in the future" in response.data

    def test_successfully_update_expense(self, client, auth):
        """Valid form should update expense and redirect."""
        auth.login()

        # Initial value
        response = client.get("/expenses/1/edit")
        assert b"Weekly groceries" in response.data
        assert b"20.5" in response.data

        # Update
        response = client.post("/expenses/1/edit", data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-10-15",
            "description": "Updated groceries"
        })
        assert response.status_code == 302
        assert response.location == "/profile"

        # Updated expense should appear in profile
        response = client.get("/profile")
        assert b"Updated groceries" in response.data
        assert b"25.00" in response.data

    def test_preserve_form_data_on_validation_error(self, client, auth):
        """Validation error should preserve form data."""
        auth.login()
        response = client.post("/expenses/1/edit", data={
            "amount": "",  # invalid
            "category": "Food",  # valid
            "date": "",  # invalid
            "description": "test"  # valid
        })
        assert response.status_code == 400
        # Form data should still be filled
        assert b"value=\"Food\"" in response.data
        assert b"value=\"test\"" in response.data


class TestDatabaseHelpers:
    """Test get_expense_by_id() and update_expense() functions."""

    def test_get_expense_by_id(self, db_session):
        """get_expense_by_id() should return expense dict or None."""
        from database.queries import get_expense_by_id

        # Existing expense for demo user
        expense = get_expense_by_id(1, 1)
        assert expense is not None
        assert expense["id"] == 1
        assert expense["amount"] == 20.5
        assert expense["category"] == "Food"

        # Non-existent expense
        expense = get_expense_by_id(1, 9999)
        assert expense is None

    def test_update_expense(self, db_session):
        """update_expense() should update and return True/False."""
        from database.queries import get_expense_by_id, update_expense

        # Get original value
        expense = get_expense_by_id(1, 1)
        assert expense is not None
        original_amount = expense["amount"]

        # Update
        success = update_expense(1, 1, 99.99, "Food", "2026-10-15", "Updated")
        assert success is True

        # Verify update
        expense = get_expense_by_id(1, 1)
        assert expense is not None
        assert expense["amount"] == 99.99
        assert expense["description"] == "Updated"


def test_flash_message_on_update(client, auth, capture_flash_messages):
    """Test that success flash message is displayed after update."""
    auth.login()

    response = client.post("/expenses/1/edit", data={
        "amount": "25.00",
        "category": "Food",
        "date": "2026-10-15",
        "description": "Updated groceries"
    })

    # Should redirect with flash message
    assert response.status_code == 302
    # Check flash message by following redirect
    response = client.get("/profile", follow_redirects=True)
    assert b"Expense updated successfully" in response.data