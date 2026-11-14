"""Bookings service: guest accounts, bookings, the reveal, history and ratings, as a JSON API."""
import logging
import os
import sys
import time
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, request

import db
from accounts import check_login, create_user, get_user, signup_errors
from restaurants_client import RestaurantsClient, RestaurantsUnavailable
from service import create_booking, get_booking, get_history, rate_booking
from tokens import make_token, read_token

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s %(levelname)s bookings %(message)s")
log = logging.getLogger("bookings")

UNAVAILABLE_MESSAGE = "We can't choose a restaurant right now. Please try again in a few minutes."


def to_json(booking):
    """A booking as JSON-friendly values (dates become text like 2026-11-20T20:00:00)."""
    return {key: (value.isoformat() if isinstance(value, datetime) else value)
            for key, value in booking.items()}


def create_app(test_config=None, restaurants=None):
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["RESTAURANTS_URL"] = os.environ.get("RESTAURANTS_URL", "http://restaurants:8000")
    app.config["RESTAURANTS_TIMEOUT_S"] = float(os.environ.get("RESTAURANTS_TIMEOUT_S", "3"))
    app.config["ALLOWED_ORIGIN"] = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")
    app.config["APP_TIMEZONE"] = os.environ.get("APP_TIMEZONE", "Europe/Madrid")
    app.config["VERSION"] = os.environ.get("GIT_SHA", "dev")
    if test_config:
        app.config.update(test_config)

    for required in ("DATABASE_URL", "SECRET_KEY"):
        if not app.config[required]:
            raise RuntimeError(f"{required} is not set")

    # Tests can pass a stand-in for the Restaurants service; normally we call it over HTTP.
    if restaurants is None:
        restaurants = RestaurantsClient(app.config["RESTAURANTS_URL"], app.config["RESTAURANTS_TIMEOUT_S"])

    # At startup: wait for the database and apply pending migrations.
    conn = db.connect(app.config["DATABASE_URL"])
    db.run_migrations(conn)
    conn.close()

    def get_conn():
        if "conn" not in g:
            g.conn = db.connect(app.config["DATABASE_URL"])
        return g.conn

    def now():
        """The current local time (dinner times are entered in this time zone)."""
        return datetime.now(ZoneInfo(app.config["APP_TIMEZONE"])).replace(tzinfo=None, microsecond=0)

    def login_required(view):
        @wraps(view)
        def wrapped(**kwargs):
            header = request.headers.get("Authorization", "")
            token = header[len("Bearer "):] if header.startswith("Bearer ") else None
            user_id = read_token(app.config["SECRET_KEY"], token)
            if user_id is None:
                return jsonify(error="not_logged_in", message="Please log in first."), 401
            g.user_id = user_id
            return view(**kwargs)
        return wrapped

    @app.teardown_appcontext
    def close_conn(error=None):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def add_cors_and_log(response):
        if request.headers.get("Origin") == app.config["ALLOWED_ORIGIN"]:
            response.headers["Access-Control-Allow-Origin"] = app.config["ALLOWED_ORIGIN"]
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Vary"] = "Origin"
        duration_ms = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
        log.info("%s %s %s %.0fms", request.method, request.path, response.status_code, duration_ms)
        return response

    @app.get("/health")
    def health():
        # Only this service's own database counts; the Restaurants service is not checked here.
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bookings")
            cursor.execute("UPDATE schema_migrations SET applied_at = applied_at WHERE 1 = 0")
            conn.rollback()
            return jsonify(status="ok", db="ok", version=app.config["VERSION"])
        except Exception as error:
            log.error("Health check failed: %s", str(error)[:200])
            return jsonify(status="error", db="unreachable", version=app.config["VERSION"]), 503

    @app.post("/signup")
    def signup():
        body = request.get_json(silent=True) or {}
        name, email, password = body.get("name", ""), body.get("email", ""), body.get("password", "")
        errors = signup_errors(name, email, password)
        if errors:
            return jsonify(errors=errors), 400
        user_id = create_user(get_conn(), name, email, password)
        if user_id is None:
            return jsonify(errors=["This email is already registered."]), 409
        return jsonify(token=make_token(app.config["SECRET_KEY"], user_id),
                       user=get_user(get_conn(), user_id)), 201

    @app.post("/login")
    def login():
        body = request.get_json(silent=True) or {}
        user_id = check_login(get_conn(), body.get("email", ""), body.get("password", ""))
        if user_id is None:
            return jsonify(errors=["Wrong email or password."]), 401
        return jsonify(token=make_token(app.config["SECRET_KEY"], user_id), user=get_user(get_conn(), user_id))

    @app.get("/me")
    @login_required
    def me():
        user = get_user(get_conn(), g.user_id)
        if user is None:
            return jsonify(error="not_logged_in", message="Please log in first."), 401
        return jsonify(user)

    @app.post("/bookings")
    @login_required
    def new_booking():
        body = request.get_json(silent=True) or {}
        budget = body.get("budget")
        try:
            booking_id, errors = create_booking(
                get_conn(), restaurants, g.user_id,
                city=body.get("city", ""),
                dinner_text=body.get("dinner_at", ""),
                theme_choice=body.get("theme_choice", ""),
                budget=budget if isinstance(budget, int) else None,
                only_new_places=bool(body.get("only_new_places")),
                now=now(),
            )
        except RestaurantsUnavailable as error:
            log.warning("Restaurants service unavailable: %s", str(error)[:200])
            return jsonify(error="restaurants_unavailable", message=UNAVAILABLE_MESSAGE), 503
        if errors:
            return jsonify(errors=errors), 400
        booking = get_booking(get_conn(), restaurants, booking_id, g.user_id, now())
        return jsonify(to_json(booking)), 201

    @app.get("/bookings")
    @login_required
    def my_bookings():
        upcoming, past = get_history(get_conn(), restaurants, g.user_id, now())
        return jsonify(upcoming=[to_json(b) for b in upcoming], past=[to_json(b) for b in past])

    @app.get("/bookings/<int:booking_id>")
    @login_required
    def one_booking(booking_id):
        booking = get_booking(get_conn(), restaurants, booking_id, g.user_id, now())
        if booking is None:
            return jsonify(error="not_found"), 404
        return jsonify(to_json(booking))

    @app.post("/bookings/<int:booking_id>/rating")
    @login_required
    def rate(booking_id):
        body = request.get_json(silent=True) or {}
        rating = body.get("rating")
        error = rate_booking(get_conn(), booking_id, g.user_id,
                             rating if isinstance(rating, int) else None, body.get("comment", ""), now())
        if error == "Booking not found.":
            return jsonify(error="not_found"), 404
        if error:
            return jsonify(errors=[error]), 400
        return jsonify(status="saved")

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)