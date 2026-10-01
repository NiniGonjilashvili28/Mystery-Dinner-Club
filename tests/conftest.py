"""Shared test setup: every test that asks for `conn` gets a fresh database."""
import pytest

from db import connect, init_db


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    init_db(str(path))
    connection = connect(str(path))
    yield connection
    connection.close()