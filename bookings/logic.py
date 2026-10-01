"""Business rules of the Bookings domain.

Like restaurants/logic.py, these functions never touch the database or the web.
The current time is always passed in as `now`, so tests can pick any moment.
"""
from datetime import datetime, timedelta

MIN_BUDGET = 30
MIN_NOTICE = timedelta(days=3)
REVEAL_BEFORE = timedelta(hours=3)
THEME_CHOICES = ["random", "luxury", "cafe", "wine_bar", "bar", "dessert"]
TIME_FORMAT = "%Y-%m-%d %H:%M"


def parse_dinner_time(text):
    """Turn the form's text (like "2026-10-08T20:00") into a datetime, or None if invalid."""
    try:
        return datetime.strptime(text.replace("T", " "), TIME_FORMAT)
    except (ValueError, AttributeError):
        return None


def validate_booking(city, dinner_at, theme_choice, budget, now, valid_cities):
    """Check a new booking. Returns a list of error messages (empty list = all good)."""
    errors = []
    if city not in valid_cities:
        errors.append("Please choose one of our cities.")
    if theme_choice not in THEME_CHOICES:
        errors.append("Please choose a theme or 'random'.")
    if budget is None or budget < MIN_BUDGET:
        errors.append(f"The minimum budget is {MIN_BUDGET}€.")
    if dinner_at is None:
        errors.append("Please choose a valid date and time.")
    elif dinner_at - now < MIN_NOTICE:
        errors.append("Bookings must be made at least 3 days in advance.")
    return errors


def reveal_time(dinner_at):
    """The moment the restaurant becomes visible: 3 hours before dinner."""
    return dinner_at - REVEAL_BEFORE


def is_revealed(dinner_at, now):
    """True once the reveal moment has arrived."""
    return now >= reveal_time(dinner_at)


def rating_error(dinner_at, current_rating, new_rating, now):
    """Check a rating. Returns an error message, or None if the rating is allowed."""
    if now < dinner_at:
        return "You can rate your dinner once it has happened."
    if current_rating is not None:
        return "You have already rated this dinner."
    if new_rating not in (1, 2, 3, 4, 5):
        return "Please choose between 1 and 5 stars."
    return None


def visited_restaurant_ids(bookings, now):
    """Ids of restaurants from the guest's past dinners (used for 'only new places')."""
    return [b["restaurant_id"] for b in bookings if b["dinner_at"] < now]


def split_upcoming_and_past(bookings, now):
    """Split bookings into (upcoming, past), so the history page can show them apart."""
    upcoming = [b for b in bookings if b["dinner_at"] >= now]
    past = [b for b in bookings if b["dinner_at"] < now]
    return upcoming, past