"""Database work of the Restaurants service (ported from restaurants/service.py to SQL Server)."""
from db import query
from logic import THEMES, pick_restaurant


def city_overview(conn):
    """Every city with how many restaurants it has per theme, sorted by city name."""
    rows = query(conn, "SELECT city, theme, COUNT(*) AS total FROM restaurants GROUP BY city, theme")
    counts = {}
    for row in rows:
        counts.setdefault(row["city"], {theme: 0 for theme in THEMES})
        counts[row["city"]][row["theme"]] = row["total"]
    return [{"city": city, "theme_counts": counts[city]} for city in sorted(counts)]


def find_restaurant_for_booking(conn, city, theme_choice, budget, exclude_ids=()):
    """Choose a secret restaurant for a booking. Returns its id, or None."""
    restaurants = query(conn, "SELECT id, city, theme, min_budget FROM restaurants WHERE city = %s", (city,))
    picked = pick_restaurant(restaurants, city, theme_choice, budget, exclude_ids)
    if picked is None:
        return None
    return picked["id"]


def get_restaurant_details(conn, restaurant_id):
    """Everything a guest sees after the reveal, or None if the id is unknown."""
    rows = query(conn, "SELECT * FROM restaurants WHERE id = %s", (restaurant_id,))
    if not rows:
        return None
    details = rows[0]
    menu = query(conn, "SELECT name, price FROM menu_items WHERE restaurant_id = %s ORDER BY id", (restaurant_id,))
    details["menu"] = [{"name": item["name"], "price": float(item["price"])} for item in menu]
    return details