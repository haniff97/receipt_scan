from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..anomalies import detect_anomalies
from ..database import get_db
from ..deepseek import judge_anomalies
from ..models import Transaction

router = APIRouter()


@router.get("/anomalies")
def anomalies(method: str = "iqr", db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    flagged = detect_anomalies(transactions, method=method)

    if flagged:
        per_cat = defaultdict(list)
        for t in transactions:
            per_cat[t.category].append(t.amount)
        context = {
            cat: {"median": sorted(vals)[len(vals) // 2], "max": max(vals), "count": len(vals)}
            for cat, vals in per_cat.items()
        }

        candidates = [
            {
                "id": t["id"],
                "date": str(t["date"]),
                "merchant": t["merchant"],
                "amount": t["amount"],
                "category": t["category"],
                "vs_median": t.get("vs_median"),
                "threshold": t.get("threshold"),
            }
            for t in flagged
        ]

        decision = judge_anomalies(candidates, context)
        if decision:
            reasons = decision.get("reasons", {})
            confirmed = [t for t in flagged if t["id"] in decision.get("confirmed", [])]
            for t in confirmed:
                t["ai_reason"] = reasons.get(str(t["id"]), "Confirmed by AI review.")
            return {
                "count": len(confirmed),
                "method": f"{method} + ai-review",
                "reviewed": True,
                "rejected": [
                    {**t, "ai_reason": reasons.get(str(t["id"]), "Normal expense per AI review.")}
                    for t in flagged
                    if t["id"] in decision.get("rejected", [])
                ],
                "anomalies": confirmed,
            }

    return {
        "count": len(flagged),
        "method": method,
        "reviewed": False,
        "anomalies": flagged,
    }
