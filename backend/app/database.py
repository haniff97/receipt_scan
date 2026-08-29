import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database URL is configurable so the same code runs on SQLite (default) or
# PostgreSQL. For Postgres set DATABASE_URL, e.g.:
#   postgresql+psycopg2://user:pass@localhost:5432/receipts
# (requires: pip install psycopg2-binary)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'receipts.db'))}",
)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# True when running on SQLite (needed for dialect-specific SQL like strftime).
IS_SQLITE = DATABASE_URL.startswith("sqlite")


class Base(DeclarativeBase):
    pass


# Single local user for now. When Supabase/Auth arrives, this becomes the
# authenticated user's id (from the JWT) — no other code changes needed.
LOCAL_USER_ID = os.environ.get("USER_ID", "local-user")


def current_user_id():
    """Return the id of the current user.

    Swap this for `request.user.id` from the auth token later. Every query in the
    app filters by this value, so per-user isolation is enforced everywhere.
    """
    return LOCAL_USER_ID


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()