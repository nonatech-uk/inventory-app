"""Connection pool, auth dependencies."""

from pathlib import Path

from mees_shared.db import get_conn, init_pool as _init_pool, close_pool  # noqa: F401
from mees_shared.auth import CurrentUser, get_current_user as _make_get_user  # noqa: F401
import mees_shared.db as _db_mod

from config.settings import settings

# App-specific auth dependency
get_current_user = _make_get_user(settings.auth_enabled, settings.dev_user_email)

_SCHEMA_FILE = Path(__file__).resolve().parent.parent.parent / "schema.sql"


def init_pool() -> None:
    _init_pool(settings.dsn, settings.db_pool_min, settings.db_pool_max)
    conn = _db_mod.pool.getconn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_FILE.read_text())
    finally:
        _db_mod.pool.putconn(conn)
