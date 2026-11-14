"""Tests for the Bookings HTTP endpoints, with a fake Restaurants service."""
from datetime import datetime, timedelta

from conftest import needs_db

pytestmark = needs_db


def in_days(days):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def sign_up(client):
    response = client.post("/signup", json={"name": "Nini", "email": "nini@example.com", "password": "longenough"})
    return {"Authorization": "Bearer " + response.get_json()["token"]}


def test_health_is_ok(client):
    assert client.get("/health").get_json()["status"] == "ok"


def test_signup_login_and_me(client):
    headers = sign_up(client)
    assert client.get("/me", headers=headers).get_json()["name"] == "Nini"
    assert client.post("/login", json={"email": "nini@example.com", "password": "longenough"}).status_code == 200
    assert client.post("/login", json={"email": "nini@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/signup", json={"name": "N", "email": "nini@example.com",
                                        "password": "longenough"}).status_code == 409
    assert client.post("/signup", json={"name": "", "email": "x", "password": "y"}).status_code == 400


def test_bookings_need_a_valid_token(client):
    assert client.get("/bookings").status_code == 401
    assert client.get("/bookings", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_book_and_see_the_secret(client):
    headers = sign_up(client)
    response = client.post("/bookings", headers=headers, json={"city": "Madrid", "dinner_at": in_days(5),
                                                                "theme_choice": "bar", "budget": 50})
    assert response.status_code == 201
    booking = response.get_json()
    assert booking["revealed"] is False and booking["restaurant"] is None
    assert client.get(f"/bookings/{booking['id']}", headers=headers).status_code == 200
    assert len(client.get("/bookings", headers=headers).get_json()["upcoming"]) == 1


def test_booking_errors_are_returned(client):
    headers = sign_up(client)
    response = client.post("/bookings", headers=headers, json={"city": "Madrid", "dinner_at": in_days(1),
                                                                "theme_choice": "bar", "budget": 50})
    assert response.status_code == 400
    assert "at least 3 days" in response.get_json()["errors"][0]


def test_booking_is_refused_clearly_when_restaurants_is_down(client, fake_restaurants):
    headers = sign_up(client)
    fake_restaurants.down = True
    response = client.post("/bookings", headers=headers, json={"city": "Madrid", "dinner_at": in_days(5),
                                                                "theme_choice": "bar", "budget": 50})
    assert response.status_code == 503
    assert response.get_json()["error"] == "restaurants_unavailable"


def test_rating_endpoint(client):
    headers = sign_up(client)
    booking = client.post("/bookings", headers=headers, json={"city": "Madrid", "dinner_at": in_days(5),
                                                               "theme_choice": "bar", "budget": 50}).get_json()
    response = client.post(f"/bookings/{booking['id']}/rating", headers=headers, json={"rating": 5})
    assert response.status_code == 400          # the dinner has not happened yet
    assert client.post("/bookings/99999/rating", headers=headers, json={"rating": 5}).status_code == 404
    assert client.get("/bookings/99999", headers=headers).status_code == 404


def test_cors_allows_only_the_ui_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://ui.test"})
    other = client.get("/health", headers={"Origin": "http://evil.test"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://ui.test"
    assert "Access-Control-Allow-Origin" not in other.headers