"""Saves and reads bookings (ported from bookings/service.py to SQL Server).

Anything about restaurants is asked from the Restaurants service through `restaurants`,
a RestaurantsClient. If that service is down, bookings still load; only the restaurant
details are missing, and creating a new booking is refused with a clear message.
"""
import random

from db import query
from logic import (
    is_revealed,
    parse_dinner_time,
    rating_error,
    reveal_time,
    split_upcoming_and_past,
    validate_booking,
    visited_restaurant_ids,
)
from restaurants_client import RestaurantsUnavailable

NO_MATCH_MESSAGE = (
    "We couldn't find a restaurant for that city, theme and budget. "
    "Try another theme, a higher budget, or untick 'only new places'."
)


def list_bookings(conn, user_id):
    """All of one guest's bookings, newest dinner first."""
    return query(conn, "SELECT * FROM bookings WHERE user_id = %s ORDER BY dinner_at DESC", (user_id,))


def create_booking(conn, restaurants, user_id, city, dinner_text, theme_choice, budget, only_new_places, now):
    """Check and save a new booking. Returns (booking_id, errors); booking_id is None if it failed.

    Raises RestaurantsUnavailable if the Restaurants service cannot be reached.
    """
    dinner_at = parse_dinner_time(dinner_text)
    errors = validate_booking(city, dinner_at, theme_choice, budget, now, restaurants.list_cities())
    if errors:
        return None, errors

    exclude_ids = []
    if only_new_places:
        exclude_ids = visited_restaurant_ids(list_bookings(conn, user_id), now)

    restaurant_id = restaurants.find_match(city, theme_choice, budget, exclude_ids)
    if restaurant_id is None:
        return None, [NO_MATCH_MESSAGE]

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookings (user_id, restaurant_id, city, dinner_at, theme_choice, budget, "
        "table_number, only_new_places, created_at) OUTPUT INSERTED.id "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (user_id, restaurant_id, city, dinner_at, theme_choice, budget,
         random.randint(1, 20), bool(only_new_places), now),
    )
    booking_id = cursor.fetchone()[0]
    conn.commit()
    return booking_id, []


def find_own_booking(conn, booking_id, user_id):
    """One booking, only if it belongs to this guest; otherwise None."""
    rows = query(conn, "SELECT * FROM bookings WHERE id = %s AND user_id = %s", (booking_id, user_id))
    return rows[0] if rows else None


def add_restaurant(booking, restaurants):
    """Attach the restaurant's details, or mark them as unavailable if the service is down."""
    booking["restaurant"] = None
    booking["restaurant_unavailable"] = False
    try:
        booking["restaurant"] = restaurants.get_details(booking["restaurant_id"])
    except RestaurantsUnavailable:
        booking["restaurant_unavailable"] = True


def get_booking(conn, restaurants, booking_id, user_id, now):
    """One booking of this guest, or None. The restaurant is only included once it is revealed."""
    booking = find_own_booking(conn, booking_id, user_id)
    if booking is None:
        return None
    booking["reveal_at"] = reveal_time(booking["dinner_at"])
    booking["revealed"] = is_revealed(booking["dinner_at"], now)
    booking["is_past"] = booking["dinner_at"] < now
    booking["restaurant"] = None
    booking["restaurant_unavailable"] = False
    if booking["revealed"]:
        add_restaurant(booking, restaurants)
    return booking


def get_history(conn, restaurants, user_id, now):
    """The guest's bookings as (upcoming, past). Past ones include the restaurant when available."""
    upcoming, past = split_upcoming_and_past(list_bookings(conn, user_id), now)
    for booking in past:
        add_restaurant(booking, restaurants)
    return upcoming, past


def rate_booking(conn, booking_id, user_id, rating, comment, now):
    """Save a rating. Returns an error message, or None if it was saved.

    Rating never needs the Restaurants service, so it still works when that service is down.
    """
    booking = find_own_booking(conn, booking_id, user_id)
    if booking is None:
        return "Booking not found."
    error = rating_error(booking["dinner_at"], booking["rating"], rating, now)
    if error:
        return error
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET rating = %s, comment = %s WHERE id = %s AND user_id = %s",
                   (rating, (comment or "").strip(), booking_id, user_id))
    conn.commit()
    return None