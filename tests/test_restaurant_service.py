"""Tests for restaurants/service.py, using a real temporary database."""
from restaurants.service import (
    find_restaurant_for_booking,
    get_restaurant_details,
    list_cities,
    theme_counts_by_city,
)


def test_list_cities_has_ten_cities_including_tbilisi(conn):
    cities = list_cities(conn)
    assert len(cities) == 10
    assert "Tbilisi" in cities


def test_every_city_has_three_restaurants_per_theme(conn):
    counts = theme_counts_by_city(conn)
    for theme_counts in counts.values():
        assert set(theme_counts.values()) == {3}


def test_find_restaurant_matches_city_theme_and_budget(conn):
    restaurant_id = find_restaurant_for_booking(conn, "Madrid", "wine_bar", 60)
    details = get_restaurant_details(conn, restaurant_id)
    assert details["city"] == "Madrid"
    assert details["theme"] == "wine_bar"
    assert details["min_budget"] <= 60


def test_find_restaurant_returns_none_for_unknown_city(conn):
    assert find_restaurant_for_booking(conn, "Atlantis", "bar", 100) is None


def test_get_restaurant_details_includes_special_menu(conn):
    row = conn.execute("SELECT id FROM restaurants WHERE offer_type = 'special' LIMIT 1").fetchone()
    details = get_restaurant_details(conn, row["id"])
    assert len(details["menu"]) == 3


def test_get_restaurant_details_returns_none_for_unknown_id(conn):
    assert get_restaurant_details(conn, 99999) is None