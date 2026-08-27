from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db, current_user_id
from ..deepseek import summarize_spending
from ..models import LhdnLimit, Transaction

router = APIRouter()

_summary_cache = {}


@router.get("/lhdn/relief")
def lhdn_relief(year: int | None = None, db: Session = Depends(get_db)):
    """Per-relief totals for a tax year, capped by the LHDN limits.

    All aggregation happens in SQL (GROUP BY) — no full-table load.
    """
    uid = current_user_id()
    # Determine applicable years
    if year is not None:
        years = [year]
    else:
        years = [r[0] for r in db.query(Transaction.tax_year).filter(Transaction.user_id == uid).distinct().all()]
        limit_years = [r[0] for r in db.query(LhdnLimit.year).distinct().all()]
        years = sorted(set(years) | set(limit_years))

    limits = {
        (l.year, l.relief_key): l.cap_amount
        for l in db.query(LhdnLimit).all()
    }

    result = []
    for y in years:
        q = db.query(
            Transaction.lhdn_relief,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        ).filter(Transaction.user_id == uid)
        if year is not None:
            q = q.filter(Transaction.tax_year == year)
        else:
            q = q.filter(Transaction.tax_year == y)
        rows = (q.group_by(Transaction.lhdn_relief).all())

        reliefs = {}
        for relief, total, count in rows:
            if not relief or relief in ("unknown", "not_claimable"):
                continue
            reliefs[relief] = {"total": round(float(total), 2), "count": count}

        # Build capped summary per relief
        capped = []
        for relief, data in reliefs.items():
            cap = limits.get((y, relief))
            total = data["total"]
            capped.append({
                "relief": relief,
                "spent": total,
                "cap": cap if cap is not None else None,
                "claimable": round(min(total, cap), 2) if cap is not None else round(total, 2),
                "count": data["count"],
            })
        capped.sort(key=lambda r: -(r["spent"] or 0))

        result.append({
            "year": y,
            "reliefs": capped,
        })

    if year is not None:
        return result[0] if result else {"year": year, "reliefs": []}
    return result


@router.get("/lhdn/summary")
def lhdn_summary(year: int | None = None, currency: str = "$", lang: str = "en", db: Session = Depends(get_db)):
    """AI summary of the user's claimable LHDN reliefs, cached by data fingerprint."""
    uid = current_user_id()
    relief_data = lhdn_relief(year=year, db=db)

    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == uid).scalar() or 0
    last = db.query(func.max(Transaction.date)).filter(Transaction.user_id == uid).scalar()
    fingerprint = (uid, count, str(last), year, currency, lang)

    if fingerprint in _summary_cache:
        return {"summary": _summary_cache[fingerprint], "cached": True}

    summary = summarize_spending(
        {"relief_summary": relief_data},
        currency=currency,
        lang=lang,
    )
    if summary:
        _summary_cache[fingerprint] = summary
        return {"summary": summary, "cached": False}

    return {"summary": "No AI key set. Enable AI to generate an LHDN summary.", "cached": False}
