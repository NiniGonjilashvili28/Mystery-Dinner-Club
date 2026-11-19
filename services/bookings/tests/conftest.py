"""Shared test setup for the Bookings service.

Database tests need a real SQL Server, found through TEST_DATABASE_URL.
WARNING: the `conn` fixture empties the users and bookings tables before each test,
so point TEST_DATABASE_URL at a database whose data you don't need.

The Restaurants service is replaced by FakeRestaurants, a stand-in we control.
"""
import os

import pytest

import db
from restaurants_client import RestaurantsUnavailable

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")


class FakeRestaurants:
    """Behaves like RestaurantsClient without any network. Madrid has bars 1, 2 and 3."""

    def __init__(self, down=False):
        self.down = down
        self.restaurants = {
            1: {"id": 1, "name": "Copper Tap", "city": "Madrid", "theme": "bar", "min_budget": 30},
            2: {"id": 2, "name": "Night Owl Bar", "city": "Madrid", "theme": "bar", "min_budget": 35},
            3: {"id": 3, "name": "The Local", "city": "Madrid", "theme": "bar", "min_budget": 40},
        }

    def _check(self):
        if self.down:
            raise RestaurantsUnavailable("Restaurants service is down")

    def list_cities(self):
        self._check()
        return ["Madrid", "Tbilisi"]

    def find_match(self, city, theme_choice, budget, exclude_ids):
        self._check()
        for r in self.restaurants.values():
            if r["city"] == city and theme_choice in ("bar", "random") \
                    and r["min_budget"] <= budget and r["id"] not in exclude_ids:
                return r["id"]
        return None

    def get_details(self, restaurant_id):
        self._check()
        return self.restaurants.get(restaurant_id)


@pytest.fixture
def conn():
    connection = db.connect(TEST_DATABASE_URL, attempts=3, first_wait=1)
    db.run_migrations(connection)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM users")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def fake_restaurants():
    return FakeRestaurants()


@pytest.fixture
def client(conn, fake_restaurants):
    from app import create_app
    app = create_app({"DATABASE_URL": TEST_DATABASE_URL, "SECRET_KEY": "test-secret",
                      "ALLOWED_ORIGIN": "http://ui.test"}, restaurants=fake_restaurants)
    return app.test_client()