"""Fills the restaurants tables with the 150 sample partner restaurants (once)."""
import json
import os

SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data.json")


def seed_restaurants(conn):
    """Insert the sample data if the table is empty. Returns how many restaurants were added."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] > 0:
        return 0

    with open(SEED_FILE, encoding="utf-8") as f:
        restaurants = json.load(f)

    for r in restaurants:
        cursor.execute(
            "INSERT INTO restaurants (name, city, theme, min_budget, address, offer_type, discount_percent) "
            "OUTPUT INSERTED.id VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (r["name"], r["city"], r["theme"], r["min_budget"], r["address"],
             r["offer_type"], r["discount_percent"]),
        )
        restaurant_id = cursor.fetchone()[0]
        for item in r["menu"]:
            cursor.execute(
                "INSERT INTO menu_items (restaurant_id, name, price) VALUES (%s, %s, %s)",
                (restaurant_id, item["name"], item["price"]),
            )
    conn.commit()
    return len(restaurants)