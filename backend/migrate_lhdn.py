"""Add LHDN columns to transactions + create lhdn_limits and seed caps.

Run: .venv/bin/python migrate_lhdn.py
Safe to run repeatedly (idempotent).
"""

import sqlalchemy as sa
from app.database import Base, engine
from app import models  # noqa: F401

LHDN_LIMITS_2025 = {
    "medical": 10000.0,
    "medical_exam": 10000.0,
    "education": 7000.0,
    "lifestyle": 2500.0,
    "sports": 1000.0,
    "childcare": 3000.0,
    "travel": 1000.0,
    "insurance": 4000.0,
    "breastfeeding": 1000.0,
    "parents_medical": 8000.0,
    "socso": 350.0,
    "epf_life": 7000.0,
}

LHDN_LIMITS_2024 = dict(LHDN_LIMITS_2025)
LHDN_LIMITS_2024["insurance"] = 3000.0


def main():
    Base.metadata.create_all(engine)

    insp = sa.inspect(engine)

    # transactions: add LHDN + user_id columns
    tx_cols = {c["name"] for c in insp.get_columns("transactions")}
    with engine.begin() as conn:
        for col, ddl in [
            ("lhdn_relief", "VARCHAR(100)"),
            ("lhdn_confidence", "FLOAT"),
            ("tax_year", "INTEGER"),
            ("user_id", "VARCHAR(100)"),
        ]:
            if col not in tx_cols:
                conn.execute(sa.text(f"ALTER TABLE transactions ADD COLUMN {col} {ddl}"))
                print(f"added transactions.{col}")
            # backfill user_id for existing rows
            if col == "user_id":
                conn.execute(sa.text("UPDATE transactions SET user_id='local-user' WHERE user_id IS NULL"))

    # receipts: add user_id column
    rc_cols = {c["name"] for c in insp.get_columns("receipts")}
    with engine.begin() as conn:
        if "user_id" not in rc_cols:
            conn.execute(sa.text("ALTER TABLE receipts ADD COLUMN user_id VARCHAR(100)"))
            print("added receipts.user_id")
        conn.execute(sa.text("UPDATE receipts SET user_id='local-user' WHERE user_id IS NULL"))

    # Seed LHDN caps
    with engine.begin() as conn:
        for year, limits in [(2025, LHDN_LIMITS_2025), (2024, LHDN_LIMITS_2024)]:
            for key, cap in limits.items():
                exists = conn.execute(
                    sa.text("SELECT 1 FROM lhdn_limits WHERE relief_key=:k AND year=:y"),
                    {"k": key, "y": year},
                ).first()
                if not exists:
                    conn.execute(
                        sa.text("INSERT INTO lhdn_limits (relief_key, year, cap_amount) VALUES (:k, :y, :c)"),
                        {"k": key, "y": year, "c": cap},
                    )
                    print(f"seeded lhdn_limits {key} {year} = {cap}")

    print("migration complete")


if __name__ == "__main__":
    main()
