"""Tests for the database work in service.py, against a real SQL Server."""
from datetime import datetime

from conftest import needs_db

from service import city_overview, find_restaurant_for_booking, get_restaurant_details, reserve_table

pytestmark = needs_db


def test_city_overview_has_ten_cities_with_three_per_theme(conn):
    overview = city_overview(conn)
    assert len(overview) == 10
    assert overview[0]["city"] == "Amsterdam"
    for city in overview:
        assert set(city["theme_counts"].values()) == {3}


def test_find_restaurant_matches_city_theme_and_budget(conn):
    restaurant_id = find_restaurant_for_booking(conn, "Madrid", "wine_bar", 60)
    details = get_restaurant_details(conn, restaurant_id)
    assert details["city"] == "Madrid"
    assert details["theme"] == "wine_bar"
    assert details["min_budget"] <= 60


def test_find_restaurant_skips_excluded_ids(conn):
    first = find_restaurant_for_booking(conn, "Madrid", "bar", 100)
    others = {find_restaurant_for_booking(conn, "Madrid", "bar", 100, exclude_ids=[first]) for _ in range(10)}
    assert first not in others


def test_find_restaurant_returns_none_for_unknown_city(conn):
    assert find_restaurant_for_booking(conn, "Atlantis", "bar", 100) is None


def test_details_include_the_special_menu(conn):
    row = conn.cursor(as_dict=True)
    row.execute("SELECT TOP 1 id FROM restaurants WHERE offer_type = 'special'")
    details = get_restaurant_details(conn, row.fetchone()["id"])
    assert len(details["menu"]) == 3
    assert isinstance(details["menu"][0]["price"], float)


def test_details_return_none_for_unknown_id(conn):
    assert get_restaurant_details(conn, 99999) is None


DINNER = datetime(2026, 12, 5, 20, 0)


def test_reserve_table_gives_each_guest_a_different_table(conn):
    first, problem = reserve_table(conn, 1, DINNER)
    second, _ = reserve_table(conn, 1, DINNER)
    assert problem is None
    assert first["table_number"] != second["table_number"]
    assert first["reservation_id"] != second["reservation_id"]


def test_reserve_table_unknown_restaurant(conn):
    assert reserve_table(conn, 99999, DINNER) == (None, "not_found")


def test_reserve_table_full_after_twenty_tables(conn):
    for _ in range(20):
        reserve_table(conn, 1, DINNER)
    assert reserve_table(conn, 1, DINNER) == (None, "full")
