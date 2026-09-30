"""Opens the SQLite database and creates the tables for both domains."""
import os
import sqlite3

from flask import current_app, g

from restaurants.seed import seed_restaurants

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILES = [
    os.path.join(BASE_DIR, "restaurants", "schema.sql"),
    os.path.join(BASE_DIR, "bookings", "schema.sql"),
]


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path):
    conn = connect(path)
    for schema_file in SCHEMA_FILES:
        with open(schema_file, encoding="utf-8") as f:
            conn.executescript(f.read())
    seed_restaurants(conn)
    conn.commit()
    conn.close()


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()