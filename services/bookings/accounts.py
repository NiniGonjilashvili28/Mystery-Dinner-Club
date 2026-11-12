"""Guest accounts: signing up and logging in (ported from bookings/accounts.py to SQL Server)."""
import pymssql
from werkzeug.security import check_password_hash, generate_password_hash

from db import query

MIN_PASSWORD_LENGTH = 8


def signup_errors(name, email, password):
    """Check the sign-up form. Returns a list of error messages (empty list = all good)."""
    errors = []
    if not name.strip():
        errors.append("Please enter your name.")
    if "@" not in email or "." not in email:
        errors.append("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Your password needs at least {MIN_PASSWORD_LENGTH} characters.")
    return errors


def create_user(conn, name, email, password):
    """Save a new guest. Returns the new user's id, or None if the email is already taken."""
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
            (name.strip(), email.strip().lower(), password_hash),
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
    except pymssql.IntegrityError:
        conn.rollback()
        return None
    return user_id


def check_login(conn, email, password):
    """Returns the user's id if the email and password are correct, otherwise None."""
    rows = query(conn, "SELECT id, password_hash FROM users WHERE email = %s", (email.strip().lower(),))
    if not rows or not check_password_hash(rows[0]["password_hash"], password):
        return None
    return rows[0]["id"]


def get_user(conn, user_id):
    """The guest's id, name and email, or None if there is no such user."""
    rows = query(conn, "SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None