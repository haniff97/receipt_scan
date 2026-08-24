import re
from collections import defaultdict
from datetime import datetime, timedelta

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

CATEGORY_WORDS = {
    "groceries": ["grocery", "groceries", "supermarket", "food shopping", "grocery store"],
    "dining": ["dining", "restaurant", "restaurants", "eating out", "coffee", "cafe", "lunch", "dinner", "takeout"],
    "transport": ["transport", "transportation", "gas", "fuel", "uber", "taxi", "ride", "commute", "driving"],
    "shopping": ["shopping", "amazon", "clothes", "clothing", "retail", "store"],
    "utilities": ["utilities", "utility", "electric", "electricity", "water", "internet", "bill", "bills", "energy"],
    "entertainment": ["entertainment", "movies", "movie", "netflix", "spotify", "streaming", "games", "concert"],
    "health": ["health", "gym", "pharmacy", "medical", "doctor", "fitness"],
    "travel": ["travel", "flight", "flights", "hotel", "airbnb", "trip", "vacation", "airline"],
}


def _match_category(q):
    for cat, words in CATEGORY_WORDS.items():
        if any(w in q for w in words):
            return cat
    return None


def _match_month(q):
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", q)
    if m:
        return MONTHS[m.group(1).lower()]
    return None


def _match_period(q):
    if any(w in q for w in ["last month", "previous month"]):
        now = datetime.now()
        first = now.replace(day=1)
        return first - timedelta(days=1), None, "last month"
    if any(w in q for w in ["this month"]):
        now = datetime.now()
        return now.replace(day=1), now, "this month"
    if any(w in q for w in ["last 30 days", "last 30 days", "past 30 days"]):
        return datetime.now() - timedelta(days=30), datetime.now(), "last 30 days"
    if any(w in q for w in ["last week", "past week"]):
        return datetime.now() - timedelta(days=7), datetime.now(), "last week"
    return None, None, None


def _match_limit(q):
    m = re.search(r"(?:top|last)\s+(\d+)\s+", q)
    return int(m.group(1)) if m else None


def run_query(q, transactions):
    q = q.lower()

    category = _match_category(q)
    month = _match_month(q)
    start, end, period_label = _match_period(q)
    limit = _match_limit(q)

    txs = transactions
    if category:
        txs = [t for t in txs if t["category"] == category]
    if month:
        txs = [t for t in txs if t["date"].month == month]
    if start:
        txs = [t for t in txs if t["date"] >= start]
    if end:
        txs = [t for t in txs if t["date"] <= end]

    wants_count = any(w in q for w in ["how many", "count", "number of"])
    wants_avg = any(w in q for w in ["average", "avg", "mean"])
    wants_total = not wants_count and not wants_avg

    result = {"query": q, "filters": {}}
    if category:
        result["filters"]["category"] = category
    if month:
        result["filters"]["month"] = month
    if period_label:
        result["filters"]["period"] = period_label

    if wants_count:
        result["answer"] = f"You made {len(txs)} transaction(s)."
        result["count"] = len(txs)
    elif wants_avg:
        avg = sum(t["amount"] for t in txs) / len(txs) if txs else 0
        result["answer"] = f"Average spend: ${avg:.2f} across {len(txs)} transaction(s)."
        result["avg"] = round(avg, 2)
    else:
        total = sum(t["amount"] for t in txs)
        result["answer"] = f"Total: ${total:.2f} across {len(txs)} transaction(s)."
        result["total"] = round(total, 2)

    txs_sorted = sorted(txs, key=lambda t: t["date"], reverse=True)
    if limit:
        txs_sorted = txs_sorted[:limit]
    result["transactions"] = [
        {
            "date": t["date"].isoformat(),
            "amount": t["amount"],
            "merchant": t["merchant"],
            "category": t["category"],
        }
        for t in txs_sorted[:20]
    ]
    return result