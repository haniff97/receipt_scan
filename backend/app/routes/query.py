from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deepseek import answer_question
from ..models import Transaction
from ..nlq import run_query

router = APIRouter()

# Cache for Ask AI answers: key = (question, lang, data_fingerprint)
_query_cache = {}


def _data_fingerprint(db: Session):
    count = db.query(func.count(Transaction.id)).scalar() or 0
    last = db.query(func.max(Transaction.date)).scalar()
    return (count, str(last))


@router.get("/query")
def query(q: str, lang: str = "en", db: Session = Depends(get_db)):
    fingerprint = _data_fingerprint(db)
    cache_key = (q.strip().lower(), lang, fingerprint)

    if cache_key in _query_cache:
        return {**_query_cache[cache_key], "cached": True}

    transactions = db.query(Transaction).order_by(Transaction.date.desc()).all()
    data = [
        {
            "date": t.date,
            "amount": t.amount,
            "merchant": t.merchant,
            "category": t.category,
        }
        for t in transactions
    ]

    ai = answer_question(q, data, lang=lang)
    if ai:
        result = {**ai, "source": "deepseek", "cached": False}
        _query_cache[cache_key] = result
        return result

    result = {**run_query(q, data), "source": "rules", "cached": False}
    _query_cache[cache_key] = result
    return result
