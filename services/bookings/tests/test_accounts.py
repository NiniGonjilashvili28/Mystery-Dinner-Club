"""Tests for sign-up and login (moved from Assignment 1, now against SQL Server)."""
from conftest import needs_db

from accounts import check_login, create_user, get_user, signup_errors


def test_signup_with_good_details_has_no_errors():
    assert signup_errors("Nini", "nini@example.com", "longenough") == []


def test_signup_needs_a_name_a_real_looking_email_and_a_long_password():
    assert len(signup_errors(" ", "not-an-email", "short")) == 3


@needs_db
def test_create_user_never_stores_the_real_password(conn):
    user_id = create_user(conn, "Nini", "nini@example.com", "longenough")
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    assert "longenough" not in cursor.fetchone()[0]


@needs_db
def test_create_user_refuses_an_email_that_is_already_used(conn):
    create_user(conn, "Nini", "nini@example.com", "longenough")
    assert create_user(conn, "Someone Else", "NINI@example.com", "otherpassword") is None


@needs_db
def test_login_checks_the_password(conn):
    user_id = create_user(conn, "Nini", "Nini@Example.com", "longenough")
    assert check_login(conn, "nini@example.com", "longenough") == user_id
    assert check_login(conn, "nini@example.com", "wrongpassword") is None
    assert check_login(conn, "nobody@example.com", "longenough") is None


@needs_db
def test_get_user_returns_name_and_email_but_no_password(conn):
    user_id = create_user(conn, "Nini", "nini@example.com", "longenough")
    assert get_user(conn, user_id) == {"id": user_id, "name": "Nini", "email": "nini@example.com"}
    assert get_user(conn, 99999) is None