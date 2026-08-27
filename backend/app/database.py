import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "receipts.db"))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


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