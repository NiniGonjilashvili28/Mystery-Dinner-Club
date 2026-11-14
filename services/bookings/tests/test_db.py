"""Tests for the database helper (the same helper as in the Restaurants service)."""
import pymssql
import pytest

import db


def test_error_number_reads_the_real_pymssql_shape():
    assert db.error_number(pymssql.OperationalError((18456, b"Login failed"))) == 18456


def test_connect_does_not_retry_a_wrong_password(monkeypatch):
    calls = []

    def fake_connect(**settings):
        calls.append(1)
        raise pymssql.OperationalError((18456, b"Login failed"))

    monkeypatch.setattr(db.pymssql, "connect", fake_connect)
    with pytest.raises(pymssql.OperationalError):
        db.connect("mssql://u:p@h/d", attempts=5)
    assert len(calls) == 1


def test_parse_database_url():
    assert db.parse_database_url("mssql://bookings_user:pw@db:1433/bookings")["database"] == "bookings"