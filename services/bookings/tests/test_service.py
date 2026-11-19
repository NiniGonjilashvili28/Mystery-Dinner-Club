"""Tests for bookings/service.py against SQL Server, with a fake Restaurants service."""
from datetime import datetime, timedelta

import pytest
from conftest import FakeRestaurants, needs_db

from accounts import create_user
from restaurants_client import RestaurantsUnavailable
from service import create_booking, get_booking, get_history, list_bookings, rate_booking

pytestmark = needs_db

NOW = datetime(2026, 10, 1, 12, 0)
DINNER_TEXT = "2026-10-08T20:00"
DINNER = datetime(2026, 10, 8, 20, 0)


@pytest.fixture
def user_id(conn):
    return create_user(conn, "Nini", "nini@example.com", "longenough")


def book(conn, restaurants, user_id, **changes):
    details = {"city": "Madrid", "dinner_text": DINNER_TEXT, "theme_choice": "bar",
               "budget": 50, "only_new_places": False, "now": NOW}
    details.update(changes)
    return create_booking(conn, restaurants, user_id, **details)


def test_create_booking_saves_it_with_the_matched_restaurant(conn, fake_restaurants, user_id):
    booking_id, errors = book(conn, fake_restaurants, user_id)
    assert errors == []
    saved = list_bookings(conn, user_id)
    assert [b["id"] for b in saved] == [booking_id]
    assert saved[0]["dinner_at"] == DINNER
    assert saved[0]["restaurant_id"] == 1


def test_create_booking_too_soon_saves_nothing(conn, fake_restaurants, user_id):
    booking_id, errors = book(conn, fake_restaurants, user_id, dinner_text="2026-10-02T20:00")
    assert booking_id is None
    assert errors == ["Bookings must be made at least 3 days in advance."]
    assert list_bookings(conn, user_id) == []


def test_create_booking_with_no_match_gives_a_message(conn, fake_restaurants, user_id):
    booking_id, errors = book(conn, fake_restaurants, user_id, theme_choice="luxury")
    assert booking_id is None
    assert "couldn't find a restaurant" in errors[0]


def test_create_booking_raises_when_restaurants_is_down(conn, user_id):
    with pytest.raises(RestaurantsUnavailable):
        book(conn, FakeRestaurants(down=True), user_id)
    assert list_bookings(conn, user_id) == []


def test_restaurant_is_hidden_before_the_reveal(conn, fake_restaurants, user_id):
    booking_id, _ = book(conn, fake_restaurants, user_id)
    booking = get_booking(conn, fake_restaurants, booking_id, user_id, now=DINNER - timedelta(hours=4))
    assert booking["revealed"] is False
    assert booking["restaurant"] is None


def test_restaurant_is_shown_after_the_reveal(conn, fake_restaurants, user_id):
    booking_id, _ = book(conn, fake_restaurants, user_id)
    booking = get_booking(conn, fake_restaurants, booking_id, user_id, now=DINNER - timedelta(hours=2))
    assert booking["revealed"] is True
    assert booking["restaurant"]["name"] == "Copper Tap"


def test_revealed_booking_still_loads_when_restaurants_is_down(conn, fake_restaurants, user_id):
    booking_id, _ = book(conn, fake_restaurants, user_id)
    booking = get_booking(conn, FakeRestaurants(down=True), booking_id, user_id, now=DINNER)
    assert booking["revealed"] is True
    assert booking["restaurant"] is None
    assert booking["restaurant_unavailable"] is True


def test_a_guest_cannot_open_someone_elses_booking(conn, fake_restaurants, user_id):
    booking_id, _ = book(conn, fake_restaurants, user_id)
    other = create_user(conn, "Other", "other@example.com", "longenough")
    assert get_booking(conn, fake_restaurants, booking_id, other, NOW) is None


def test_only_new_places_skips_visited_restaurants(conn, fake_restaurants, user_id):
    visited = []
    now = NOW
    for _ in range(3):
        dinner = now + timedelta(days=4)
        booking_id, errors = book(conn, fake_restaurants, user_id, only_new_places=True, now=now,
                                  dinner_text=dinner.strftime("%Y-%m-%dT%H:%M"))
        assert errors == []
        visited.append(list_bookings(conn, user_id)[0]["restaurant_id"])
        now = dinner + timedelta(days=1)
    assert sorted(visited) == [1, 2, 3]


def test_history_splits_upcoming_and_past(conn, fake_restaurants, user_id):
    book(conn, fake_restaurants, user_id)
    upcoming, past = get_history(conn, fake_restaurants, user_id, now=DINNER + timedelta(days=1))
    assert upcoming == [] and len(past) == 1
    assert past[0]["restaurant"]["name"] == "Copper Tap"


def test_rating_rules(conn, fake_restaurants, user_id):
    booking_id, _ = book(conn, fake_restaurants, user_id)
    after = DINNER + timedelta(days=1)
    assert rate_booking(conn, booking_id, user_id, 5, "", NOW) == "You can rate your dinner once it has happened."
    assert rate_booking(conn, booking_id, user_id, 5, " Loved it! ", after) is None
    assert rate_booking(conn, booking_id, user_id, 1, "", after) == "You have already rated this dinner."
    assert rate_booking(conn, 99999, user_id, 5, "", after) == "Booking not found."