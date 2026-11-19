"""Shared test setup for the Restaurants service.

Database tests need a real SQL Server. They read its address from TEST_DATABASE_URL
(locally: the compose database; in CI: a SQL Server service container).
Without it, those tests are skipped and only the pure logic tests run.
"""
import os

import pytest

import db
from seed import seed_restaurants

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")


@pytest.fixture
def conn():
    connection = db.connect(TEST_DATABASE_URL, attempts=3, first_wait=1)
    db.run_migrations(connection)
    seed_restaurants(connection)
    yield connection
    connection.close()


@pytest.fixture
def client():
    from app import create_app
    app = create_app({"DATABASE_URL": TEST_DATABASE_URL, "ALLOWED_ORIGIN": "http://ui.test"})
    return app.test_client()
