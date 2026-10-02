"""A few end-to-end checks: the pages work together in a real (temporary) app."""
import sqlite3
from datetime import datetime, timedelta

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


def sign_up(client):
    return client.post("/signup", data={"name": "Nini", "email": "nini@example.com",
                                        "password": "longenough"}, follow_redirects=True)


def in_days(days):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def test_home_and_cities_pages_open(client):
    assert client.get("/").status_code == 200
    assert b"Tbilisi" in client.get("/cities").data


def test_booking_page_needs_login(client):
    response = client.get("/book")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_guest_can_sign_up_book_and_sees_secret(client):
    sign_up(client)
    response = client.post("/book", data={"city": "Madrid", "dinner_at": in_days(5),
                                          "theme_choice": "random", "budget": "50"},
                           follow_redirects=True)
    assert "Your restaurant is a secret" in response.get_data(as_text=True)


def test_booking_too_soon_shows_the_error(client):
    sign_up(client)
    response = client.post("/book", data={"city": "Madrid", "dinner_at": in_days(1),
                                          "theme_choice": "bar", "budget": "50"})
    assert "at least 3 days in advance" in response.get_data(as_text=True)


def test_past_dinner_is_revealed_and_can_be_rated(app, client):
    sign_up(client)
    client.post("/book", data={"city": "Madrid", "dinner_at": in_days(5),
                               "theme_choice": "bar", "budget": "50"})
    # Move the dinner into the past, as if a week had gone by.
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE bookings SET dinner_at = '2026-01-01 20:00'")
    conn.commit()
    conn.close()

    page = client.get("/bookings/1").get_data(as_text=True)
    assert "is reserved under your name" in page
    client.post("/bookings/1/rate", data={"rating": "4", "comment": "Great"})
    assert "★★★★☆" in client.get("/bookings/1").get_data(as_text=True)
    assert "Places you've visited" in client.get("/my-dinners").get_data(as_text=True)


def test_login_logout_and_wrong_password(client):
    sign_up(client)
    client.post("/logout")
    wrong = client.post("/login", data={"email": "nini@example.com", "password": "nope"})
    assert "Wrong email or password" in wrong.get_data(as_text=True)
    right = client.post("/login", data={"email": "nini@example.com", "password": "longenough"})
    assert right.status_code == 302


def test_unknown_booking_gives_404(client):
    sign_up(client)
    assert client.get("/bookings/999").status_code == 404