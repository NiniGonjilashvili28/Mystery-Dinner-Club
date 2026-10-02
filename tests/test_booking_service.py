"""Tests for bookings/service.py, using a real temporary database."""
from datetime import datetime, timedelta

import pytest

from bookings.accounts import create_user
from bookings.service import create_booking, get_booking, get_history, list_bookings, rate_booking

NOW = datetime(2026, 10, 1, 12, 0)
DINNER_TEXT = "2026-10-08T20:00"
DINNER = datetime(2026, 10, 8, 20, 0)


@pytest.fixture
def user_id(conn):
    return create_user(conn, "Nini", "nini@example.com", "longenough")


def book(conn, user_id, **changes):
    """Make a booking that works. Each test changes only what it needs."""
    details = {"city": "Madrid", "dinner_text": DINNER_TEXT, "theme_choice": "bar",
               "budget": 50, "only_new_places": False, "now": NOW}
    details.update(changes)
    return create_booking(conn, user_id, **details)


def test_create_booking_saves_it_for_the_guest(conn, user_id):
    booking_id, errors = book(conn, user_id)
    assert errors == []
    saved = list_bookings(conn, user_id)
    assert [b["id"] for b in saved] == [booking_id]
    assert saved[0]["dinner_at"] == DINNER


def test_create_booking_too_soon_saves_nothing(conn, user_id):
    booking_id, errors = book(conn, user_id, dinner_text="2026-10-02T20:00")
    assert booking_id is None
    assert errors == ["Bookings must be made at least 3 days in advance."]
    assert list_bookings(conn, user_id) == []


def test_create_booking_with_no_matching_restaurant_gives_message(conn, user_id):
    booking_id, errors = book(conn, user_id, theme_choice="luxury", budget=30)
    assert booking_id is None
    assert "couldn't find a restaurant" in errors[0]


def test_restaurant_is_hidden_before_the_reveal(conn, user_id):
    booking_id, _ = book(conn, user_id)
    booking = get_booking(conn, booking_id, user_id, now=DINNER - timedelta(hours=4))
    assert booking["revealed"] is False
    assert booking["restaurant"] is None


def test_restaurant_is_shown_after_the_reveal(conn, user_id):
    booking_id, _ = book(conn, user_id)
    booking = get_booking(conn, booking_id, user_id, now=DINNER - timedelta(hours=2))
    assert booking["revealed"] is True
    assert booking["restaurant"]["city"] == "Madrid"
    assert booking["restaurant"]["theme"] == "bar"


def test_a_guest_cannot_open_someone_elses_booking(conn, user_id):
    booking_id, _ = book(conn, user_id)
    other_user = create_user(conn, "Other", "other@example.com", "longenough")
    assert get_booking(conn, booking_id, other_user, NOW) is None


def test_only_new_places_never_repeats_a_visited_restaurant(conn, user_id):
    # Madrid has 3 bars. Visit them one by one; each new booking must be a different one.
    visited = []
    now = NOW
    for _ in range(3):
        dinner = now + timedelta(days=4)
        booking_id, errors = book(conn, user_id, only_new_places=True, now=now,
                                  dinner_text=dinner.strftime("%Y-%m-%dT%H:%M"))
        assert errors == []
        visited.append(list_bookings(conn, user_id)[0]["restaurant_id"])
        now = dinner + timedelta(days=1)   # time passes, the dinner is now in the past
    assert len(set(visited)) == 3

    # A fourth booking has nowhere new to go.
    dinner = now + timedelta(days=4)
    booking_id, errors = book(conn, user_id, only_new_places=True, now=now,
                              dinner_text=dinner.strftime("%Y-%m-%dT%H:%M"))
    assert booking_id is None


def test_history_splits_upcoming_and_past(conn, user_id):
    book(conn, user_id)
    upcoming, past = get_history(conn, user_id, now=NOW)
    assert len(upcoming) == 1 and past == []
    upcoming, past = get_history(conn, user_id, now=DINNER + timedelta(days=1))
    assert upcoming == [] and len(past) == 1
    assert past[0]["restaurant"]["name"]


def test_rating_is_saved_after_the_dinner(conn, user_id):
    booking_id, _ = book(conn, user_id)
    after = DINNER + timedelta(days=1)
    assert rate_booking(conn, booking_id, user_id, 5, " Loved it! ", after) is None
    booking = get_booking(conn, booking_id, user_id, after)
    assert booking["rating"] == 5
    assert booking["comment"] == "Loved it!"


def test_rating_before_the_dinner_is_refused(conn, user_id):
    booking_id, _ = book(conn, user_id)
    assert rate_booking(conn, booking_id, user_id, 5, "", NOW) == \
        "You can rate your dinner once it has happened."


def test_rating_twice_is_refused(conn, user_id):
    booking_id, _ = book(conn, user_id)
    after = DINNER + timedelta(days=1)
    rate_booking(conn, booking_id, user_id, 5, "", after)
    assert rate_booking(conn, booking_id, user_id, 1, "", after) == \
        "You have already rated this dinner."


def test_rating_someone_elses_booking_is_refused(conn, user_id):
    booking_id, _ = book(conn, user_id)
    other_user = create_user(conn, "Other", "other@example.com", "longenough")
    assert rate_booking(conn, booking_id, other_user, 5, "", DINNER + timedelta(days=1)) == \
        "Booking not found."