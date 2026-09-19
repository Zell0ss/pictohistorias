# backend/db/session.py
from backend.clients import settings
from lib.db import get_connection


def get_db():
    conn = get_connection(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    try:
        yield conn
    finally:
        conn.close()
