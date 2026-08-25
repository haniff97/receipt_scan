from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deepseek import summarize_spending
from ..database import get_db
from ..models import Receipt, Transaction
from ..schemas import TransactionCreate, TransactionOut

router = APIRouter()


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    category: str | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if category:
        q = q.filter(Transaction.category == category)
    if start:
        q = q.filter(Transaction.date >= datetime.combine(start, time.min))
    if end:
        q = q.filter(Transaction.date <= datetime.combine(end, time.max))
    return q.order_by(Transaction.date.desc()).all()


@router.post("/transactions", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = Transaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return {"deleted": tx_id}


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in payload.model_dump().items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = (
        db.query(Transaction.category, func.count(Transaction.id), func.sum(Transaction.amount))
        .group_by(Transaction.category)
        .all()
    )
    return [
        {"category": c, "count": n, "total": round(float(t), 2)}
        for c, n, t in rows
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.sum(Transaction.amount)).scalar() or 0
    count = db.query(func.count(Transaction.id)).scalar() or 0
    first = db.query(func.min(Transaction.date)).scalar()
    last = db.query(func.max(Transaction.date)).scalar()
    return {
        "total_spent": round(float(total), 2),
        "transaction_count": count,
        "first_date": first,
        "last_date": last,
    }

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_today - timedelta(days=start_today.weekday())
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = db.query(Transaction.date, Transaction.category, Transaction.amount).all()

    today = sum(a for d, _, a in rows if d >= start_today)
    week = sum(a for d, _, a in rows if d >= start_week)
    month = sum(a for d, _, a in rows if d >= start_month)

    monthly = {}
    for d, _, a in rows:
        key = d.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + a

    by_cat = {}
    for _, c, a in rows:
        by_cat[c] = by_cat.get(c, 0) + a

    month_names = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
        "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }

    return {
        "today": round(today, 2),
        "week": round(week, 2),
        "month": round(month, 2),
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

    now = datetime.now()
    rows = db.query(Transaction.date, Transaction.category, Transaction.amount).all()

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
    summary = summarize_spending(data, currency=currency, lang=lang)
    return {
        "summary": summary or "No DeepSeek API key set. Add one to enable AI summaries.",
    }