import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"


def _chat(messages, temperature=0):
    if not API_KEY:
        return None
    body = json.dumps(
        {"model": MODEL, "messages": messages, "temperature": temperature}
    ).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


CATEGORIES = "groceries, dining, transport, shopping, utilities, entertainment, health, travel"


def enhance_ocr(ocr_text):
    """Send messy OCR text to DeepSeek, get back clean structured receipt JSON."""
    messages = [
        {
            "role": "system",
            "content": (
                "You extract data from messy OCR receipt text. "
                "Fix OCR errors (e.g. '1674' total means 16.74, 'CORNERCAFE' means 'Corner Cafe'). "
                "YOUR PRIMARY TASK — find the FINAL TOTAL the customer paid: "
                "NEVER return SUBTOTAL — ignore lines with 'SUBTOTAL', 'Sub Total', 'Sub-total'. "
                "Scan every line for a final TOTAL keyword and take the number right next to it. "
                "Look for lines like: TOTAL, GRAND TOTAL, TOTAL (RM), TOTAL DUE, NET TOTAL, "
                "AMOUNT DUE, BAYARAN, JUMLAH, KESELURUHAN, CASH, RM (usually near the bottom). "
                "If you SEE a printed final total line, set 'total' to that number and "
                "'total_method' to 'printed'. "
                "If NO printed total line exists, sum the item prices and add tax, and set "
                "'total_method' to 'computed'. "
                "Correct misread digits (e.g. '1674' = 16.74, '4346' = 43.46, '433' could be 43.3). "
                "Round to 2 decimals. "
                f"Return ONLY valid JSON with keys: "
                f'"merchant" (string), "total" (number), "total_method" ("printed" or "computed"), '
                f'"date" (YYYY-MM-DD or null), '
                f'"category" (one of: {CATEGORIES}), "items" (list of {{"name","price"}}).'
            ),
        },
        {"role": "user", "content": ocr_text},
    ]
    content = _chat(messages)
    if not content:
        return None
    try:
        start, end = content.find("{"), content.rfind("}")
        return json.loads(content[start : end + 1])
    except Exception:
        return None


def verify_and_correct_total(ai):
    """Validate the AI's total using the method it reported.

    The AI reports 'total_method':
      - "printed"  → it SAW a printed final total line → trust it exactly.
      - "computed" → it summed item prices itself → trust its sum directly
                     (do NOT add tax again — the AI already accounted for it).
      - missing    → older/fallback responses → only correct if clearly subtotal.

    Returns the corrected total (float) or None.
    """
    if not ai:
        return None

    ai_total = ai.get("total")
    if not isinstance(ai_total, (int, float)):
        return None
    ai_total = float(ai_total)

    method = ai.get("total_method")

    # Both "printed" and "computed" — trust the AI's value directly.
    if method in ("printed", "computed"):
        return round(ai_total, 2)

    # Legacy fallback (no total_method): only nudge if AI total looks like
    # a bare subtotal (matches item sum exactly) and tax info is present.
    items = ai.get("items") or []
    prices = [
        float(i["price"])
        for i in items
        if isinstance(i, dict) and isinstance(i.get("price"), (int, float)) and i["price"] > 0
    ]
    if prices:
        subtotal = round(sum(prices), 2)
        if abs(ai_total - subtotal) < 0.05 and ai.get("tax"):
            # Only apply tax if the receipt explicitly states a tax rate
            tax_rate = float(ai.get("tax", 0)) / 100
            if tax_rate > 0:
                return round(subtotal * (1 + tax_rate), 2)
    return round(ai_total, 2)


def summarize_spending(dashboard_data, currency="$"):
    """Generate a friendly plain-English summary of the dashboard."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a personal finance assistant. Summarize the user's spending "
                "in 2-4 concise, friendly sentences. Highlight the biggest category, "
                "how this month compares to last, and any notable changes. "
                f"Use the currency symbol '{currency}' before every amount "
                f"(e.g. '{currency}43.46' or 'RM 43.46'), never '$' unless '{currency}' is '$'. "
                "Use plain language, no markdown."
            ),
        },
        {"role": "user", "content": json.dumps(dashboard_data)},
    ]
    return _chat(messages, temperature=0.5)


def answer_question(question, transactions):
    """Answer a natural-language question using real transaction data via DeepSeek.

    Returns a dict matching the rule-based NLQ shape:
    {answer, filters, transactions} — or None if unavailable/failed.
    """
    sample = transactions[:200]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a personal finance assistant with access to the user's "
                "transactions. Answer their question accurately using the data. "
                "Return ONLY valid JSON with keys: "
                '"answer" (string, 1-2 sentences with RM amounts), '
                '"filters" (object describing what you filtered by), '
                '"transactions" (array of up to 10 matching items, each '
                '{"date","merchant","amount","category"}). '
                'If no transactions match, set "transactions" to [] and say so in the answer.'
            ),
        },
        {
            "role": "user",
            "content": (
                f"QUESTION: {question}\n\n"
                f"TRANSACTIONS (date ISO, merchant, amount, category):\n"
                f"{json.dumps(sample, default=str)}"
            ),
        },
    ]
    content = _chat(messages, temperature=0)
    if not content:
        return None
    try:
        start, end = content.find("{"), content.rfind("}")
        data = json.loads(content[start : end + 1])
        if "answer" not in data:
            return None
        data.setdefault("filters", {})
        data.setdefault("transactions", [])
        return data
    except Exception:
        return None


def judge_anomalies(candidates, context):
    """Let DeepSeek decide which candidate transactions are true anomalies.

    candidates: list of {id, date, merchant, amount, category, vs_median, threshold}
    context:    summary of each category (median, typical range) for grounding.
    Returns a dict {confirmed: [...], rejected: [...], reasons: {...}} or None.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a fraud/finance analyst reviewing potential spending anomalies. "
                "A candidate was statistically flagged because its amount is well above "
                "the typical range for its category. Decide if it is a GENUINE anomaly "
                "(e.g. a large one-off or suspicious purchase) or a NORMAL expense "
                "(e.g. annual bills, family events, big but expected purchases). "
                "Return ONLY valid JSON: "
                '{"confirmed":[ids...], "rejected":[ids...], '
                '"reasons":{"<id>":"short explanation"}}. '
                "Only include an id in exactly one of confirmed/rejected."
            ),
        },
        {
            "role": "user",
            "content": (
                f"CATEGORY CONTEXT (median and typical max per category):\n"
                f"{json.dumps(context)}\n\n"
                f"CANDIDATES:\n{json.dumps(candidates, default=str)}"
            ),
        },
    ]
    content = _chat(messages, temperature=0)
    if not content:
        return None
    try:
        start, end = content.find("{"), content.rfind("}")
        data = json.loads(content[start : end + 1])
        if "confirmed" not in data:
            return None
        return data
    except Exception:
        return None