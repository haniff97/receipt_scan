"""Gemini vision-based receipt extraction.

Gemini reads the receipt image DIRECTLY (no tesseract OCR needed), which is far
more accurate on real phone photos. Falls back gracefully when no API key is set.
"""

import base64
import io
import json
import os
import urllib.request

from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

API_KEY = os.environ.get("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")

CATEGORIES = "groceries, dining, transport, shopping, utilities, entertainment, health, travel"


def _detect_mime(image_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes so Gemini receives the correct type."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    if image_bytes[:4] in (b'\x00\x00\x00\x18', b'\x00\x00\x00\x1c') or b'ftyp' in image_bytes[:12]:
        return "image/heic"
    if image_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    return "image/jpeg"  # safe default


def _resize_for_gemini(image_bytes: bytes, max_side: int = 1600, quality: int = 85) -> bytes:
    """Downscale image so the longest side is <= max_side and re-encode as JPEG.

    Gemini API works best under ~1MB. Phone photos are often 3-10MB which can
    trigger 404/413 errors or degrade reading accuracy.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


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


def extract_receipt(image_bytes: bytes, mime: str | None = None) -> dict | None:
    """Send a receipt image to Gemini vision and get structured JSON back.

    Returns a dict matching the enhance_ocr shape, or None if unavailable/failed.
    """
    if not API_KEY:
        return None

    if mime is None:
        mime = _detect_mime(image_bytes)
    # Resize to max 1600px and compress — Gemini struggles with large images
    image_bytes = _resize_for_gemini(image_bytes)
    mime = "image/jpeg"  # always JPEG after resize
    print(f"[Gemini] Sending {len(image_bytes)//1024}KB image as {mime} via model={MODEL}")
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
        print(f"[Gemini] Raw result → total={result.get('total')}, method={result.get('total_method')}, merchant={result.get('merchant')}")
        if "total" not in result:
            return None
        result.setdefault("merchant", "Unknown")
        result.setdefault("date", None)
        result.setdefault("items", [])
        return result
    except Exception as e:
        print(f"[Gemini] ERROR: {e}")
        return None
