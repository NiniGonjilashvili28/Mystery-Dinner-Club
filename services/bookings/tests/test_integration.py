"""Integration tests across the seam.

Bookings runs for real (its Flask app and its own SQL Server database) and talks over real HTTP,
through RestaurantsClient and its timeout, to a stand-in Restaurants service. The stand-in answers
like the real one does in services/restaurants/openapi.yaml. Why a stand-in and not the real
service: see ADR-9.
"""
import threading
import time
from datetime import datetime, timedelta

import pytest
from flask import Flask, jsonify, request
from werkzeug.serving import make_server

from conftest import TEST_DATABASE_URL, needs_db
from restaurants_client import RestaurantsClient

pytestmark = needs_db


def make_restaurants_stub(delay_s=0):
    """A small Flask app with the same endpoints and answers as the Restaurants service."""
    stub = Flask("restaurants_stub")
    stub.calls = []

    @stub.before_request
    def record_and_wait():
        stub.calls.append(f"{request.method} {request.path}")
        time.sleep(delay_s)                  # a slow Restaurants service

    @stub.get("/cities")
    def cities():
        counts = {"luxury": 3, "cafe": 3, "wine_bar": 3, "bar": 3, "dessert": 3}
        return jsonify(cities=[{"city": "Madrid", "theme_counts": counts}], themes=list(counts))

    @stub.post("/matches")
    def matches():
        return jsonify(restaurant_id=7)

    @stub.post("/reservations")
    def reservations():
        return jsonify(reservation_id=1, table_number=12), 201

    @stub.get("/restaurants/<int:restaurant_id>")
    def details(restaurant_id):
        return jsonify(id=restaurant_id, name="Copper Tap", city="Madrid", theme="bar", min_budget=30,
                       address="Calle Mayor 1", offer_type="discount", discount_percent=15, menu=[])

    return stub


@pytest.fixture
def start_stub():
    """Starts stand-in Restaurants services on free ports; stops them after the test."""
    servers = []

    def start(delay_s=0):
        stub = make_restaurants_stub(delay_s)
        server = make_server("127.0.0.1", 0, stub, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return stub, f"http://127.0.0.1:{server.server_port}"

    yield start
    for server in servers:
        server.shutdown()


def bookings_client(base_url, timeout_s):
    from app import create_app
    restaurants = RestaurantsClient(base_url, timeout_s=timeout_s)
    app = create_app({"DATABASE_URL": TEST_DATABASE_URL, "SECRET_KEY": "test-secret",
                      "ALLOWED_ORIGIN": "http://ui.test"}, restaurants=restaurants)
    client = app.test_client()
    token = client.post("/signup", json={"name": "Nini", "email": "nini@example.com",
                                         "password": "longenough"}).get_json()["token"]
    return client, {"Authorization": "Bearer " + token}


def booking_request():
    dinner = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
    return {"city": "Madrid", "dinner_at": dinner, "theme_choice": "bar", "budget": 50, "party_size": 3}


def test_a_booking_crosses_the_seam_over_http(conn, start_stub):
    stub, url = start_stub()
    client, headers = bookings_client(url, timeout_s=3)

    response = client.post("/bookings", headers=headers, json=booking_request())

    assert response.status_code == 201
    booking = response.get_json()
    assert booking["table_number"] == 12            # chosen and reserved by Restaurants
    assert booking["party_size"] == 3
    assert stub.calls == ["GET /cities", "POST /matches", "POST /reservations"]


def test_a_slow_restaurants_service_gives_a_clear_503_within_the_timeout(conn, start_stub):
    _, url = start_stub(delay_s=2)
    client, headers = bookings_client(url, timeout_s=0.5)

    started = time.monotonic()
    response = client.post("/bookings", headers=headers, json=booking_request())
    elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.get_json()["error"] == "restaurants_unavailable"
    assert elapsed < 1.5                            # gave up after the timeout, did not hang
    assert client.get("/bookings", headers=headers).status_code == 200   # the rest still works
