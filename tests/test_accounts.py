"""Tests for sign-up and login in bookings/accounts.py."""
from bookings.accounts import check_login, create_user, get_user, signup_errors


def test_signup_with_good_details_has_no_errors():
    assert signup_errors("Nini", "nini@example.com", "longenough") == []


def test_signup_needs_a_name():
    assert signup_errors("   ", "nini@example.com", "longenough") == ["Please enter your name."]


def test_signup_needs_a_real_looking_email():
    assert signup_errors("Nini", "not-an-email", "longenough") == ["Please enter a valid email address."]


def test_signup_refuses_short_password():
    assert signup_errors("Nini", "nini@example.com", "short") == \
        ["Your password needs at least 8 characters."]


def test_create_user_never_stores_the_real_password(conn):
    user_id = create_user(conn, "Nini", "nini@example.com", "longenough")
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    assert "longenough" not in row["password_hash"]


def test_create_user_refuses_an_email_that_is_already_used(conn):
    create_user(conn, "Nini", "nini@example.com", "longenough")
    assert create_user(conn, "Someone Else", "nini@example.com", "otherpassword") is None


def test_login_with_correct_password_returns_user_id(conn):
    user_id = create_user(conn, "Nini", "nini@example.com", "longenough")
    assert check_login(conn, "nini@example.com", "longenough") == user_id


def test_login_ignores_capital_letters_in_email(conn):
    user_id = create_user(conn, "Nini", "Nini@Example.com", "longenough")
    assert check_login(conn, "nini@example.com", "longenough") == user_id


def test_login_with_wrong_password_fails(conn):
    create_user(conn, "Nini", "nini@example.com", "longenough")
    assert check_login(conn, "nini@example.com", "wrongpassword") is None


def test_login_with_unknown_email_fails(conn):
    assert check_login(conn, "nobody@example.com", "longenough") is None


def test_get_user_returns_name_and_email_but_no_password(conn):
    user_id = create_user(conn, "Nini", "nini@example.com", "longenough")
    assert get_user(conn, user_id) == {"id": user_id, "name": "Nini", "email": "nini@example.com"}


def test_get_user_returns_none_for_unknown_id(conn):
    assert get_user(conn, 99999) is None