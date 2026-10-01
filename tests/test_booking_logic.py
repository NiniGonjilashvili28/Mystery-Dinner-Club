"""Tests for the booking rules in bookings/logic.py."""
from datetime import datetime, timedelta

from bookings.logic import (
    is_revealed,
    parse_dinner_time,
    rating_error,
    reveal_time,
    split_upcoming_and_past,
    validate_booking,
    visited_restaurant_ids,
)

# A fixed "now", so every test uses the same moment.
NOW = datetime(2026, 10, 1, 12, 0)
CITIES = ["Madrid", "Tbilisi"]


def valid_booking(**changes):
    """A booking that passes every rule. Each test changes one thing."""
    booking = {
        "city": "Madrid",
        "dinner_at": NOW + timedelta(days=5),
        "theme_choice": "bar",
        "budget": 50,
    }
    booking.update(changes)
    return validate_booking(now=NOW, valid_cities=CITIES, **booking)


# --- parse_dinner_time ---

def test_parse_dinner_time_reads_form_format():
    assert parse_dinner_time("2026-10-08T20:00") == datetime(2026, 10, 8, 20, 0)


def test_parse_dinner_time_returns_none_for_garbage():
    assert parse_dinner_time("next friday") is None


def test_parse_dinner_time_returns_none_for_missing_value():
    assert parse_dinner_time(None) is None


# --- validate_booking ---

def test_valid_booking_has_no_errors():
    assert valid_booking() == []


def test_booking_less_than_3_days_ahead_is_refused():
    errors = valid_booking(dinner_at=NOW + timedelta(days=2, hours=23))
    assert errors == ["Bookings must be made at least 3 days in advance."]


def test_booking_exactly_3_days_ahead_is_allowed():
    assert valid_booking(dinner_at=NOW + timedelta(days=3)) == []


def test_budget_under_30_is_refused():
    assert valid_booking(budget=29) == ["The minimum budget is 30€."]


def test_budget_exactly_30_is_allowed():
    assert valid_booking(budget=30) == []


def test_missing_budget_is_refused():
    assert valid_booking(budget=None) == ["The minimum budget is 30€."]


def test_unknown_city_is_refused():
    assert valid_booking(city="Atlantis") == ["Please choose one of our cities."]


def test_unknown_theme_is_refused():
    assert valid_booking(theme_choice="karaoke") == ["Please choose a theme or 'random'."]


def test_random_theme_is_allowed():
    assert valid_booking(theme_choice="random") == []


def test_invalid_date_is_refused():
    assert valid_booking(dinner_at=None) == ["Please choose a valid date and time."]


def test_several_problems_give_several_errors():
    assert len(valid_booking(city="Atlantis", budget=10)) == 2


# --- the 3-hour reveal ---

DINNER = datetime(2026, 10, 8, 20, 0)


def test_reveal_time_is_3_hours_before_dinner():
    assert reveal_time(DINNER) == datetime(2026, 10, 8, 17, 0)


def test_not_revealed_one_minute_before_reveal():
    assert not is_revealed(DINNER, now=datetime(2026, 10, 8, 16, 59))


def test_revealed_exactly_at_reveal_time():
    assert is_revealed(DINNER, now=datetime(2026, 10, 8, 17, 0))


def test_still_revealed_after_dinner():
    assert is_revealed(DINNER, now=datetime(2026, 10, 9, 10, 0))


# --- ratings ---

def test_rating_after_dinner_is_allowed():
    assert rating_error(DINNER, None, 5, now=DINNER + timedelta(hours=3)) is None


def test_rating_before_dinner_is_refused():
    assert rating_error(DINNER, None, 5, now=DINNER - timedelta(hours=1)) == \
        "You can rate your dinner once it has happened."


def test_rating_twice_is_refused():
    assert rating_error(DINNER, 4, 5, now=DINNER + timedelta(days=1)) == \
        "You have already rated this dinner."


def test_rating_outside_1_to_5_is_refused():
    assert rating_error(DINNER, None, 6, now=DINNER + timedelta(days=1)) == \
        "Please choose between 1 and 5 stars."


# --- history and only new places ---

BOOKINGS = [
    {"restaurant_id": 7, "dinner_at": NOW - timedelta(days=10)},   # past
    {"restaurant_id": 9, "dinner_at": NOW + timedelta(days=4)},    # upcoming
]


def test_visited_ids_only_counts_past_dinners():
    assert visited_restaurant_ids(BOOKINGS, NOW) == [7]


def test_split_upcoming_and_past():
    upcoming, past = split_upcoming_and_past(BOOKINGS, NOW)
    assert [b["restaurant_id"] for b in upcoming] == [9]
    assert [b["restaurant_id"] for b in past] == [7]