"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

import sqlite3

from pyromind.catalog.db import get_connection


def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection for the request scope."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
