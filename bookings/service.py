"""Saves and reads bookings, using the rules in bookings/logic.py.

Anything about restaurants is asked from restaurants/service.py.
This file never reads the restaurants tables itself.
"""
import random
from datetime import datetime

from bookings.logic import (
    TIME_FORMAT,
    is_revealed,
    parse_dinner_time,
    rating_error,
    reveal_time,
    split_upcoming_and_past,
    validate_booking,
    visited_restaurant_ids,
)
from restaurants.service import find_restaurant_for_booking, get_restaurant_details, list_cities

NO_MATCH_MESSAGE = (
    "We couldn't find a restaurant for that city, theme and budget. "
    "Try another theme, a higher budget, or untick 'only new places'."
)


def list_bookings(conn, user_id):
    """All of one guest's bookings, newest dinner first, with dinner_at as a real datetime."""
    rows = conn.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY dinner_at DESC", (user_id,)
    ).fetchall()
    bookings = []
    for row in rows:
        booking = dict(row)
        booking["dinner_at"] = datetime.strptime(booking["dinner_at"], TIME_FORMAT)
        bookings.append(booking)
    return bookings


def create_booking(conn, user_id, city, dinner_text, theme_choice, budget, only_new_places, now):
    """Check and save a new booking. Returns (booking_id, errors); booking_id is None if it failed."""
    dinner_at = parse_dinner_time(dinner_text)
    errors = validate_booking(city, dinner_at, theme_choice, budget, now, list_cities(conn))
    if errors:
        return None, errors

    exclude_ids = []
    if only_new_places:
        exclude_ids = visited_restaurant_ids(list_bookings(conn, user_id), now)

    restaurant_id = find_restaurant_for_booking(conn, city, theme_choice, budget, exclude_ids)
    if restaurant_id is None:
        return None, [NO_MATCH_MESSAGE]

    cursor = conn.execute(
        "INSERT INTO bookings (user_id, restaurant_id, city, dinner_at, theme_choice, budget, "
        "table_number, only_new_places, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, restaurant_id, city, dinner_at.strftime(TIME_FORMAT), theme_choice, budget,
         random.randint(1, 20), int(only_new_places), now.strftime(TIME_FORMAT)),
    )
    conn.commit()
    return cursor.lastrowid, []


def get_booking(conn, booking_id, user_id, now):
    """One booking of this guest, or None. The restaurant is only included once it is revealed."""
    for booking in list_bookings(conn, user_id):
        if booking["id"] == booking_id:
            booking["reveal_at"] = reveal_time(booking["dinner_at"])
            booking["revealed"] = is_revealed(booking["dinner_at"], now)
            booking["is_past"] = booking["dinner_at"] < now
            booking["restaurant"] = None
            if booking["revealed"]:
                booking["restaurant"] = get_restaurant_details(conn, booking["restaurant_id"])
            return booking
    return None


def get_history(conn, user_id, now):
    """The guest's bookings as (upcoming, past). Past ones include the restaurant name."""
    upcoming, past = split_upcoming_and_past(list_bookings(conn, user_id), now)
    for booking in past:
        booking["restaurant"] = get_restaurant_details(conn, booking["restaurant_id"])
    return upcoming, past


def rate_booking(conn, booking_id, user_id, rating, comment, now):
    """Save a rating. Returns an error message, or None if it was saved."""
    booking = get_booking(conn, booking_id, user_id, now)
    if booking is None:
        return "Booking not found."
    error = rating_error(booking["dinner_at"], booking["rating"], rating, now)
    if error:
        return error
    conn.execute(
        "UPDATE bookings SET rating = ?, comment = ? WHERE id = ? AND user_id = ?",
        (rating, comment.strip(), booking_id, user_id),
    )
    conn.commit()
    return None