"""Database access for the Restaurants service: connecting, and running migrations."""
import logging
import os
import time
from urllib.parse import unquote, urlparse

import pymssql

log = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")


def parse_database_url(url):
    """Split mssql://user:password@host:port/database into the parts pymssql needs."""
    parts = urlparse(url)
    return {
        "server": parts.hostname,
        "port": parts.port or 1433,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": parts.path.lstrip("/"),
    }

def error_number(error):
    """The SQL Server error number inside a pymssql error, e.g. 18456 or 40613.

    pymssql wraps the details as a pair (number, message) inside the error.
    """
    first = error.args[0] if error.args else None
    if isinstance(first, tuple) and first:
        first = first[0]
    return first


def is_login_failure(error):
    """True if SQL Server refused the user name or password (error number 18456)."""
    return error_number(error) == 18456
def connect(url, attempts=6, first_wait=2.0):
    """Open a connection, retrying with growing waits.

    On Azure the database pauses when idle and needs up to about a minute to resume;
    connections fail meanwhile, so we try again: 2s, 4s, 8s, 16s, 32s between attempts.
    """
    settings = parse_database_url(url)
    wait = first_wait
    for attempt in range(1, attempts + 1):
        try:
            return pymssql.connect(login_timeout=15, timeout=30, **settings)
        except pymssql.OperationalError as error:
            # A wrong user or password (error 18456) will not fix itself, so give up at once.
            if attempt == attempts or is_login_failure(error):
                raise
            log.warning("Database not reachable (attempt %d/%d): %s. Retrying in %.0fs",
                        attempt, attempts, str(error)[:120], wait)
            time.sleep(wait)
            wait *= 2


def query(conn, sql, params=()):
    """Run a SELECT and return the rows as a list of dictionaries."""
    cursor = conn.cursor(as_dict=True)
    cursor.execute(sql, params or None)
    return cursor.fetchall()


def run_migrations(conn, folder=MIGRATIONS_DIR):
    """Apply every migration file that has not been applied yet, in order.

    Each file runs exactly once: its name is recorded in schema_migrations,
    in the same transaction as the migration itself.
    Returns the names of the files applied now (an empty list if none).
    """
    cursor = conn.cursor()
    cursor.execute(
        "IF OBJECT_ID('schema_migrations') IS NULL "
        "CREATE TABLE schema_migrations ("
        "  version NVARCHAR(255) PRIMARY KEY,"
        "  applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME())"
    )
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    already_applied = {row[0] for row in cursor.fetchall()}

    applied_now = []
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".sql") or filename in already_applied:
            continue
        with open(os.path.join(folder, filename), encoding="utf-8") as f:
            sql = f.read()
        try:
            cursor.execute(sql)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (filename,))
            conn.commit()
        except Exception:
            conn.rollback()
            log.error("Migration %s failed and was rolled back", filename)
            raise
        log.info("Applied migration %s", filename)
        applied_now.append(filename)

    if not applied_now:
        log.info("No pending migrations")
    return applied_now