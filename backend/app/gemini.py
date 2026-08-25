"""Gemini vision-based receipt extraction.

Gemini reads the receipt image DIRECTLY (no tesseract OCR needed), which is far
more accurate on real phone photos. Falls back gracefully when no API key is set.
"""

import base64
import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

API_KEY = os.environ.get("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

CATEGORIES = "groceries, dining, transport, shopping, utilities, entertainment, health, travel"

PROMPT = (
    "You are an expert receipt reader. Look at this receipt image and extract its data. "
    "Read every line carefully.\n"
    "CRITICAL — the 'total' MUST be the FINAL GRAND TOTAL the customer pays, NOT the subtotal.\n"
    "Rules for the 'total':\n"
    "1. NEVER use SUBTOTAL — ignore lines containing 'SUBTOTAL', 'Sub Total', 'Sub-total'.\n"
    "2. Look for the FINAL TOTAL line: TOTAL, GRAND TOTAL, TOTAL (RM), TOTAL DUE, "
    "BAYARAN, JUMLAH, KESELURUHAN, AMOUNT DUE, NET TOTAL, or a 'RM' amount near the bottom. "
    "The total is the number on that exact line.\n"
    "3. If you SEE a printed final TOTAL line, set 'total' to that exact number and "
    "set 'total_method' to 'printed'.\n"
    "4. If NO printed total line exists, sum the item prices, add any tax percentage shown "
    "(e.g. 6% SST), and set 'total_method' to 'computed'.\n"
    "5. Correct any misread digits (e.g. '4346' = 43.46, '25.5' = 25.50). Round to 2 decimals.\n"
    f'Return ONLY valid JSON with keys: "merchant" (string), "total" (number), '
    f'"total_method" ("printed" or "computed"), "date" (YYYY-MM-DD or null), '
    f'"category" (one of: {CATEGORIES}), '
    f'"items" (list of {{"name", "price"}}).'
)


def extract_receipt(image_bytes: bytes, mime: str = "image/jpeg") -> dict | None:
    """Send a receipt image to Gemini vision and get structured JSON back.

    Returns a dict matching the enhance_ocr shape, or None if unavailable/failed.
    """
    if not API_KEY:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    body = json.dumps({
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/{MODEL}:generateContent?key={API_KEY}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        start, end = text.find("{"), text.rfind("}")
        result = json.loads(text[start : end + 1])
        if "total" not in result:
            return None
        result.setdefault("merchant", "Unknown")
        result.setdefault("date", None)
        result.setdefault("items", [])
        return result
    except Exception:
        return None
