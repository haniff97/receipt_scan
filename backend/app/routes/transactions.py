from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deepseek import summarize_spending
from ..database import get_db, current_user_id
from ..models import Receipt, Transaction
from ..schemas import TransactionCreate, TransactionOut

router = APIRouter()

# Cache for AI dashboard summaries: key = (data_fingerprint, currency, lang)
_summary_cache = {}


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    category: str | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == current_user_id())
    if category:
        q = q.filter(Transaction.category == category)
    if start:
        q = q.filter(Transaction.date >= datetime.combine(start, time.min))
    if end:
        q = q.filter(Transaction.date <= datetime.combine(end, time.max))
    return q.order_by(Transaction.date.desc()).all()


@router.post("/transactions", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = Transaction(**payload.model_dump(), user_id=current_user_id())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx_id, Transaction.user_id == current_user_id())
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return {"deleted": tx_id}


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx_id, Transaction.user_id == current_user_id())
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in payload.model_dump().items():
        setattr(tx, field, value)
    # If a user overrides the relief, mark it as user-confirmed and refresh tax year.
    if "lhdn_relief" in payload.model_dump():
        tx.tax_year = tx.date.year if tx.date else None
        if payload.lhdn_relief:
            tx.lhdn_confidence = 1.0  # user confirmed
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = (
        db.query(Transaction.category, func.count(Transaction.id), func.sum(Transaction.amount))
        .filter(Transaction.user_id == current_user_id())
        .group_by(Transaction.category)
        .all()
    )
    return [
        {"category": c, "count": n, "total": round(float(t), 2)}
        for c, n, t in rows
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    uid = current_user_id()
    total = db.query(func.sum(Transaction.amount)).filter(Transaction.user_id == uid).scalar() or 0
    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == uid).scalar() or 0
    first = db.query(func.min(Transaction.date)).filter(Transaction.user_id == uid).scalar()
    last = db.query(func.max(Transaction.date)).filter(Transaction.user_id == uid).scalar()
    return {
        "total_spent": round(float(total), 2),
        "transaction_count": count,
        "first_date": first,
        "last_date": last,
    }

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from sqlalchemy import case

    uid = current_user_id()
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_today - timedelta(days=start_today.weekday())
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Today / week / month in one pass using conditional SUMs — no full-table load.
    today = db.query(
        func.coalesce(func.sum(case((Transaction.date >= start_today, Transaction.amount), else_=0)), 0)
    ).filter(Transaction.user_id == uid).scalar()
    week = db.query(
        func.coalesce(func.sum(case((Transaction.date >= start_week, Transaction.amount), else_=0)), 0)
    ).filter(Transaction.user_id == uid).scalar()
    month = db.query(
        func.coalesce(func.sum(case((Transaction.date >= start_month, Transaction.amount), else_=0)), 0)
    ).filter(Transaction.user_id == uid).scalar()

    # Monthly totals via SQL GROUP BY (strftime works on SQLite; use DATE_TRUNC for Postgres later).
    monthly_rows = (
        db.query(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount),
        )
        .filter(Transaction.user_id == uid)
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly = {key: float(total) for key, total in monthly_rows}

    # Category totals via SQL GROUP BY.
    by_cat_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount),
        )
        .filter(Transaction.user_id == uid)
        .group_by(Transaction.category)
        .all()
    )
    by_cat = {c: float(t) for c, t in by_cat_rows}

    month_names = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
        "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }

    return {
        "today": round(float(today), 2),
        "week": round(float(week), 2),
        "month": round(float(month), 2),
        "monthly": [
            {"month": f"{month_names[key[5:]]} {key[:4]}", "total": round(total, 2)}
            for key, total in sorted(monthly.items())
        ],
        "byCategory": [
            {"category": c, "total": round(t, 2)}
            for c, t in sorted(by_cat.items(), key=lambda kv: -kv[1])
        ],
    }

@router.get("/dashboard/summary")
def dashboard_summary(currency: str = "$", lang: str = "en", db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    uid = current_user_id()
    now = datetime.now()
    rows = (
        db.query(Transaction.date, Transaction.category, Transaction.amount)
        .filter(Transaction.user_id == uid)
        .all()
    )

    monthly = {}
    for d, _, a in rows:
        key = d.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + a

    by_cat = {}
    for _, c, a in rows:
        by_cat[c] = by_cat.get(c, 0) + a

    data = {
        "total_spent": round(sum(a for _, _, a in rows), 2),
        "monthly": monthly,
        "by_category": by_cat,
    }

    # Only regenerate when new data arrives (new receipt), not on every dashboard open.
    count = len(rows)
    last_date = max((r[0] for r in rows), default=None)
    fingerprint = (count, str(last_date))
    cache_key = (fingerprint, currency, lang)

    if cache_key in _summary_cache:
        return {"summary": _summary_cache[cache_key], "cached": True}

    summary = summarize_spending(data, currency=currency, lang=lang)
    if summary:
        _summary_cache[cache_key] = summary
        return {"summary": summary, "cached": False}

    return {
        "summary": "No DeepSeek API key set. Add one to enable AI summaries.",
        "cached": False,
    }