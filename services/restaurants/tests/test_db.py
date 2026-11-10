"""Tests for connecting, migrations and seeding."""
import pymssql
import pytest
from conftest import needs_db

import db
from seed import seed_restaurants


class FakeConnect:
    """Stands in for pymssql.connect: fails a given number of times, then succeeds."""

    def __init__(self, failures, error_number=40613):
        self.failures = failures
        self.error_number = error_number
        self.calls = 0

    def __call__(self, **settings):
        self.calls += 1
        if self.calls <= self.failures:
            # Same shape as a real pymssql error: one argument, a pair (number, message).
            raise pymssql.OperationalError((self.error_number, b"not available"))
        return "connection"


def test_connect_retries_until_the_database_answers(monkeypatch):
    fake = FakeConnect(failures=2)
    monkeypatch.setattr(db.pymssql, "connect", fake)
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)
    assert db.connect("mssql://u:p@h/d", attempts=5) == "connection"
    assert fake.calls == 3


def test_connect_gives_up_after_the_last_attempt(monkeypatch):
    fake = FakeConnect(failures=10)
    monkeypatch.setattr(db.pymssql, "connect", fake)
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)
    with pytest.raises(pymssql.OperationalError):
        db.connect("mssql://u:p@h/d", attempts=3)
    assert fake.calls == 3


def test_connect_does_not_retry_a_wrong_password(monkeypatch):
    fake = FakeConnect(failures=10, error_number=18456)
    monkeypatch.setattr(db.pymssql, "connect", fake)
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)
    with pytest.raises(pymssql.OperationalError):
        db.connect("mssql://u:p@h/d", attempts=5)
    assert fake.calls == 1

def test_error_number_reads_the_real_pymssql_shape():
    assert db.error_number(pymssql.OperationalError((18456, b"Login failed"))) == 18456
    assert db.error_number(pymssql.OperationalError((40613, b"Not available"))) == 40613
def test_parse_database_url_splits_all_parts():
    settings = db.parse_database_url("mssql://restaurants_user:Pa%40ss-1@db:1433/restaurants")
    assert settings == {"server": "db", "port": 1433, "user": "restaurants_user",
                        "password": "Pa@ss-1", "database": "restaurants"}


def test_parse_database_url_uses_default_port():
    assert db.parse_database_url("mssql://u:p@myserver/mydb")["port"] == 1433


@needs_db
def test_migrations_run_only_once(conn):
    # The fixture already applied everything, so a second run applies nothing.
    assert db.run_migrations(conn) == []
    rows = db.query(conn, "SELECT version FROM schema_migrations ORDER BY version")
    assert rows[0]["version"] == "001_init.sql"


@needs_db
def test_seeding_twice_adds_nothing(conn):
    assert seed_restaurants(conn) == 0
    total = db.query(conn, "SELECT COUNT(*) AS total FROM restaurants")[0]["total"]
    assert total == 150