"""Guest accounts for the Bookings domain: signing up and logging in."""
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

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
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash),
        )
    except sqlite3.IntegrityError:
        return None
    conn.commit()
    return cursor.lastrowid


def check_login(conn, email, password):
    """Returns the user's id if the email and password are correct, otherwise None."""
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    if row is None:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return row["id"]


def get_user(conn, user_id):
    """The guest's id, name and email, or None if there is no such user."""
    row = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return dict(row)