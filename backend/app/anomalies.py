from collections import defaultdict


def detect_anomalies(transactions, method="iqr", k=1.5):
    """Flag transactions whose amount is unusually high for their category.

    method='iqr' -> IQR fences (median-based, robust to outliers).
    method='zscore' -> mean/std based (can be skewed by the outliers themselves).
    k is the multiplier on the IQR/standard-deviation band.
    """
    txs = [
        {
            "id": t.id,
            "date": t.date,
            "amount": t.amount,
            "merchant": t.merchant,
            "category": t.category,
        }
        for t in transactions
    ]

    by_cat = defaultdict(list)
    for t in txs:
        by_cat[t["category"]].append(t["amount"])

    flagged = []
    for cat, amounts in by_cat.items():
        if len(amounts) < 2:
            continue

        if len(amounts) >= 6:
            # IQR fences (robust for larger samples)
            sorted_a = sorted(amounts)
            n = len(sorted_a)
            q1 = sorted_a[n // 4]
            q3 = sorted_a[(3 * n) // 4]
            iqr = q3 - q1
            if iqr == 0:
                continue
            upper = q3 + k * iqr
        else:
            # Small sample (2-5 items): IQR is unstable (the anomaly skews its own
            # quartiles), so flag anything > 2x the max of the others.
            sorted_a = sorted(amounts)
            upper = sorted_a[-2] * 2 if len(sorted_a) >= 2 else 0

        for t in txs:
            if t["category"] == cat and t["amount"] > upper:
                median = sorted_a[len(sorted_a) // 2]
                t["threshold"] = round(upper, 2)
                t["deviation_pct"] = round((t["amount"] - upper) / upper * 100, 1)
                t["vs_median"] = round(t["amount"] / median, 1) if median else 1.0
                flagged.append(t)

    flagged.sort(key=lambda t: t["amount"], reverse=True)
    return flagged


def summarize_anomalies(flagged):
    if not flagged:
        return "No anomalies detected."
    lines = [f"{len(flagged)} unusual transaction(s) found:"]
    for t in flagged:
        lines.append(
            f"- {t['date'].date()}: {t['merchant']} ${t['amount']:.2f} "
            f"({t['category']}) — {t['vs_median']:.1f}x your usual spend"
        )
    return "\n".join(lines)