from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deepseek import answer_question
from ..models import Transaction
from ..nlq import run_query

router = APIRouter()


@router.get("/query")
def query(q: str, lang: str = "en", db: Session = Depends(get_db)):
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
        return {**ai, "source": "deepseek"}

    return {**run_query(q, data), "source": "rules"}
