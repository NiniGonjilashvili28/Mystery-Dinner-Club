"""Database work of the Restaurants service (ported from restaurants/service.py to SQL Server)."""
import random

from db import query
from logic import THEMES, choose_table, pick_restaurant


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


def reserve_table(conn, restaurant_id, dinner_at, rng=random):
    """Reserve a free table at this restaurant for this dinner time.

    Returns (reservation, problem): reservation is {"reservation_id", "table_number"},
    and problem is None, "not_found" (unknown restaurant) or "full" (every table taken).
    """
    if not query(conn, "SELECT id FROM restaurants WHERE id = %s", (restaurant_id,)):
        return None, "not_found"
    rows = query(conn, "SELECT table_number FROM reservations WHERE restaurant_id = %s AND dinner_at = %s",
                 (restaurant_id, dinner_at))
    table_number = choose_table([row["table_number"] for row in rows], rng)
    if table_number is None:
        return None, "full"
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reservations (restaurant_id, dinner_at, table_number) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
        (restaurant_id, dinner_at, table_number),
    )
    reservation_id = cursor.fetchone()[0]
    conn.commit()
    return {"reservation_id": reservation_id, "table_number": table_number}, None
