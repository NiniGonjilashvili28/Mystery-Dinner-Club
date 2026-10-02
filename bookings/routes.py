"""Web pages of the Bookings domain: accounts, booking a dinner, history and ratings."""
from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from bookings.accounts import check_login, create_user, get_user, signup_errors
from bookings.logic import MIN_BUDGET, THEME_CHOICES
from bookings.service import create_booking, get_booking, get_history, rate_booking
from db import get_db
from restaurants.service import list_cities

bp = Blueprint("bookings", __name__)


@bp.before_app_request
def load_logged_in_user():
    """Before every page: find out who is logged in (or nobody)."""
    user_id = session.get("user_id")
    g.user = get_user(get_db(), user_id) if user_id else None


def login_required(view):
    """Pages marked with @login_required send guests to the login page first."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in first.")
            return redirect(url_for("bookings.login"))
        return view(**kwargs)
    return wrapped_view


def to_int(text):
    """Turn form text into a whole number, or None if it isn't one."""
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    errors = []
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        errors = signup_errors(name, email, password)
        if not errors:
            user_id = create_user(get_db(), name, email, password)
            if user_id is None:
                errors = ["This email is already registered."]
            else:
                session.clear()
                session["user_id"] = user_id
                return redirect(url_for("bookings.new_booking"))
    return render_template("signup.html", errors=errors)


@bp.route("/login", methods=["GET", "POST"])
def login():
    errors = []
    if request.method == "POST":
        user_id = check_login(get_db(), request.form.get("email", ""), request.form.get("password", ""))
        if user_id is None:
            errors = ["Wrong email or password."]
        else:
            session.clear()
            session["user_id"] = user_id
            return redirect(url_for("bookings.my_dinners"))
    return render_template("login.html", errors=errors)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@bp.route("/book", methods=["GET", "POST"])
@login_required
def new_booking():
    db = get_db()
    errors = []
    if request.method == "POST":
        booking_id, errors = create_booking(
            db,
            user_id=g.user["id"],
            city=request.form.get("city", ""),
            dinner_text=request.form.get("dinner_at", ""),
            theme_choice=request.form.get("theme_choice", ""),
            budget=to_int(request.form.get("budget")),
            only_new_places=request.form.get("only_new_places") == "on",
            now=datetime.now(),
        )
        if not errors:
            flash("Your mystery dinner is booked!")
            return redirect(url_for("bookings.booking_detail", booking_id=booking_id))
    return render_template("book.html", errors=errors, cities=list_cities(db),
                           themes=THEME_CHOICES, min_budget=MIN_BUDGET)


@bp.route("/bookings/<int:booking_id>")
@login_required
def booking_detail(booking_id):
    booking = get_booking(get_db(), booking_id, g.user["id"], datetime.now())
    if booking is None:
        return render_template("not_found.html"), 404
    return render_template("booking.html", booking=booking)


@bp.route("/bookings/<int:booking_id>/rate", methods=["POST"])
@login_required
def rate(booking_id):
    error = rate_booking(get_db(), booking_id, g.user["id"], to_int(request.form.get("rating")),
                         request.form.get("comment", ""), datetime.now())
    flash(error or "Thank you for your rating!")
    return redirect(url_for("bookings.booking_detail", booking_id=booking_id))


@bp.route("/my-dinners")
@login_required
def my_dinners():
    upcoming, past = get_history(get_db(), g.user["id"], datetime.now())
    return render_template("my_dinners.html", upcoming=upcoming, past=past)