"""Restaurants service: partner restaurants and the matching logic, as a JSON API."""
import logging
import os
import sys
import time

from flask import Flask, g, jsonify, request

import db
from logic import THEMES
from seed import seed_restaurants
from service import city_overview, find_restaurant_for_booking, get_restaurant_details

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s %(levelname)s restaurants %(message)s")
log = logging.getLogger("restaurants")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL")
    app.config["ALLOWED_ORIGIN"] = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")
    app.config["VERSION"] = os.environ.get("GIT_SHA", "dev")
    if test_config:
        app.config.update(test_config)

    if not app.config["DATABASE_URL"]:
        raise RuntimeError("DATABASE_URL is not set")

    # At startup: wait for the database, apply pending migrations, add sample data if empty.
    conn = db.connect(app.config["DATABASE_URL"])
    db.run_migrations(conn)
    added = seed_restaurants(conn)
    if added:
        log.info("Seeded %d sample restaurants", added)
    conn.close()

    def get_conn():
        if "conn" not in g:
            g.conn = db.connect(app.config["DATABASE_URL"])
        return g.conn

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
        # CORS: only the UI's own address may call this service from a browser.
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
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM restaurants")          # can read
            cursor.execute("UPDATE schema_migrations SET applied_at = applied_at WHERE 1 = 0")  # can write
            conn.rollback()
            return jsonify(status="ok", db="ok", version=app.config["VERSION"])
        except Exception as error:
            log.error("Health check failed: %s", str(error)[:200])
            return jsonify(status="error", db="unreachable", version=app.config["VERSION"]), 503

    @app.get("/cities")
    def cities():
        return jsonify(cities=city_overview(get_conn()), themes=THEMES)

    @app.post("/matches")
    def match():
        body = request.get_json(silent=True) or {}
        city = body.get("city")
        theme_choice = body.get("theme_choice")
        budget = body.get("budget")
        exclude_ids = body.get("exclude_ids", [])
        if not isinstance(city, str) or not isinstance(theme_choice, str) \
                or not isinstance(budget, int) or not isinstance(exclude_ids, list):
            return jsonify(error="bad_request",
                           message="Send city, theme_choice, budget (whole number) and exclude_ids (list)."), 400
        restaurant_id = find_restaurant_for_booking(get_conn(), city, theme_choice, budget, exclude_ids)
        if restaurant_id is None:
            return jsonify(error="no_match"), 404
        return jsonify(restaurant_id=restaurant_id)

    @app.get("/restaurants/<int:restaurant_id>")
    def restaurant(restaurant_id):
        details = get_restaurant_details(get_conn(), restaurant_id)
        if details is None:
            return jsonify(error="not_found"), 404
        return jsonify(details)

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)