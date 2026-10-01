"""The public "front door" of the Restaurants domain.

Other parts of the app (like Bookings) must only use these functions.
They never read the restaurants tables themselves.
"""
from restaurants.logic import THEMES, pick_restaurant


def list_cities(conn):
    """All cities that have partner restaurants, in alphabetical order."""
    rows = conn.execute("SELECT DISTINCT city FROM restaurants ORDER BY city").fetchall()
    return [row["city"] for row in rows]


def theme_counts_by_city(conn):
    """How many restaurants each city has per theme, e.g. {"Madrid": {"bar": 3, ...}}."""
    rows = conn.execute(
        "SELECT city, theme, COUNT(*) AS total FROM restaurants GROUP BY city, theme"
    ).fetchall()
    counts = {}
    for row in rows:
        counts.setdefault(row["city"], {theme: 0 for theme in THEMES})
        counts[row["city"]][row["theme"]] = row["total"]
    return counts


def find_restaurant_for_booking(conn, city, theme_choice, budget, exclude_ids=()):
    """Choose a secret restaurant for a booking. Returns its id, or None."""
    rows = conn.execute(
        "SELECT id, city, theme, min_budget FROM restaurants WHERE city = ?", (city,)
    ).fetchall()
    restaurants = [dict(row) for row in rows]
    picked = pick_restaurant(restaurants, city, theme_choice, budget, exclude_ids)
    if picked is None:
        return None
    return picked["id"]


def get_restaurant_details(conn, restaurant_id):
    """Everything a guest sees after the reveal, or None if the id is unknown."""
    row = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
    if row is None:
        return None
    details = dict(row)
    menu = conn.execute(
        "SELECT name, price FROM menu_items WHERE restaurant_id = ? ORDER BY id", (restaurant_id,)
    ).fetchall()
    details["menu"] = [dict(item) for item in menu]
    return details