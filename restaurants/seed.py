"""Fills the Restaurants tables with sample partner restaurants."""
import json
import os

SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_data.json")


def seed_restaurants(conn):
    already_there = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
    if already_there > 0:
        return

    with open(SEED_FILE, encoding="utf-8") as f:
        restaurants = json.load(f)

    for r in restaurants:
        cursor = conn.execute(
            "INSERT INTO restaurants (name, city, theme, min_budget, address, offer_type, discount_percent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["name"], r["city"], r["theme"], r["min_budget"], r["address"],
             r["offer_type"], r["discount_percent"]),
        )
        restaurant_id = cursor.lastrowid
        for item in r["menu"]:
            conn.execute(
                "INSERT INTO menu_items (restaurant_id, name, price) VALUES (?, ?, ?)",
                (restaurant_id, item["name"], item["price"]),
            )