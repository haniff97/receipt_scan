import io
import re
from datetime import datetime

import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
from pillow_heif import register_heif_opener

from .deskew import deskew

register_heif_opener()


def deskew_bytes(image_bytes: bytes) -> bytes:
    """Deskew an image (JPEG/PNG/WebP/HEIC/etc.) and return re-encoded PNG bytes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    corrected = deskew(arr)
    out = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(out)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def _preprocess(img: Image.Image) -> Image.Image:
    """Improve OCR accuracy: grayscale, upscale small images, boost contrast."""
    img = img.convert("L")
    w, h = img.size
    if max(w, h) < 1500:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return img


def image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Open an image file (JPEG/PNG/WebP/HEIC/etc.) and return an RGB PIL image."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.convert("RGB")


def is_pdf(image_bytes: bytes) -> bool:
    return image_bytes[:5] == b"%PDF-"


def image_from_pdf(pdf_bytes: bytes, dpi: int = 200) -> Image.Image:
    """Render the first page of a PDF to a PIL image for OCR."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def open_as_image(image_bytes: bytes) -> Image.Image:
    """Open bytes as an RGB image, handling both image formats and PDFs."""
    if is_pdf(image_bytes):
        return image_from_pdf(image_bytes)
    return image_from_bytes(image_bytes)


def ocr_image(image_bytes: bytes) -> str:
    """Run tesseract on an image (or first page of a PDF) and return raw text."""
    img = open_as_image(image_bytes)
    img = _preprocess(img)
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