import io
import re
from datetime import datetime

import pytesseract
from PIL import Image


def ocr_image(image_bytes: bytes) -> str:
    """Run tesseract on an image and return raw extracted text."""
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img)


def parse_receipt(text: str) -> dict:
    """Extract merchant, total, and date from raw OCR text. Returns None for missing fields."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    merchant = lines[0][:200] if lines else "Unknown"

    total = None
    total_re = re.compile(
        r"(?:total|amount|grand total)[:$]?\s*[\$€£]?\s*(\d+(?:[.,]\d{2})?)",
        re.IGNORECASE,
    )
    for line in lines:
        m = total_re.search(line)
        if m:
            raw = m.group(1)
            if "." in raw or "," in raw:
                total = float(raw.replace(",", "."))
            else:
                total = float(raw)
                if total >= 100:
                    total /= 100  # "1674" => 16.74
            break

    date = None
    date_re = re.compile(
        r"(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})"
    )
    for line in lines:
        m = date_re.search(line)
        if m:
            try:
                day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if year < 100:
                    year += 2000
                date = datetime(year, mon, day)
                break
            except ValueError:
                continue

    return {
        "merchant": merchant,
        "total": total,
        "date": date,
    }