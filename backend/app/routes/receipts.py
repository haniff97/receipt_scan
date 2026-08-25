import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pillow_heif import register_heif_opener
from sqlalchemy.orm import Session

from ..deepseek import enhance_ocr, verify_and_correct_total
from ..gemini import extract_receipt
from ..database import get_db
from ..models import Receipt, Transaction
from ..schemas import ReceiptCreateResponse
from ..ocr import ocr_image, open_as_image, parse_receipt, exif_correct_bytes

register_heif_opener()

router = APIRouter()

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/receipts/upload", response_model=ReceiptCreateResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    category: str = "groceries",
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()
    is_pdf_file = image_bytes[:5] == b"%PDF-"

    # Apply EXIF orientation before anything else.
    # Phone cameras store rotation in EXIF — raw bytes are sideways.
    # Gemini API does NOT reliably honour EXIF, so bake the rotation in.
    if not is_pdf_file:
        try:
            gemini_bytes = exif_correct_bytes(image_bytes)
        except Exception:
            gemini_bytes = image_bytes
    else:
        gemini_bytes = image_bytes

    display_bytes = gemini_bytes  # save the same corrected image to disk

    # 1) PRIMARY: Gemini vision reads the corrected image (most accurate)
    ai = None
    if not is_pdf_file:
        ai = extract_receipt(gemini_bytes, mime="image/jpeg")

    # 2) FALLBACK: tesseract OCR + DeepSeek cleanup
    text = ""
    if ai is None:
        try:
            text = ocr_image(display_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    # Duplicate check — only meaningful when we have actual OCR text.
    # When Gemini succeeds, text is "" so we skip to avoid false positives.
    if text:
        existing = (
            db.query(Receipt)
            .filter(Receipt.ocr_text == text)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"This receipt was already uploaded (id={existing.id}). "
                       f"Scan a different receipt.",
            )

    parsed = parse_receipt(text) if text else {"total": None, "merchant": "Unknown", "date": None}

    if ai is None:
        ai = enhance_ocr(text)
    if ai and ai.get("total"):
        total = verify_and_correct_total(ai)
        if total is None:
            total = float(ai["total"])
        merchant = ai.get("merchant") or "Unknown"
        category = ai.get("category") or category
        try:
            tx_date = datetime.fromisoformat(ai["date"]) if ai.get("date") else datetime.now()
        except (ValueError, TypeError):
            tx_date = datetime.now()
        # Sanitize: receipts are scanned when spent — reject clearly wrong dates
        # (future, or more than a year old) so "today" queries stay accurate.
        now_dt = datetime.now()
        if tx_date > now_dt + timedelta(days=1) or tx_date < now_dt - timedelta(days=365):
            tx_date = now_dt
    else:
        parsed = parse_receipt(text)
        if parsed["total"] is None:
            raise HTTPException(
                status_code=422,
                detail="Could not find a total amount on the receipt. "
                       f"OCR text was: {text[:300]}",
            )
        total = parsed["total"]
        merchant = parsed["merchant"]
        tx_date = parsed["date"] or datetime.now()

    receipt = Receipt(filename=file.filename or "receipt.png", ocr_text=text)
    db.add(receipt)
    db.flush()

    image_path = os.path.join(UPLOAD_DIR, f"{receipt.id}.png")
    img = open_as_image(display_bytes)
    img.save(image_path, "PNG")

    tx = Transaction(
        date=tx_date,
        amount=total,
        merchant=merchant,
        category=category,
        description=f"Uploaded from receipt: {receipt.filename}",
        receipt_id=receipt.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(receipt)
    db.refresh(tx)

    return {
        "id": receipt.id,
        "filename": receipt.filename,
        "transactions_created": 1,
        "ocr_text": text[:500],
        "image_url": f"/api/receipts/{receipt.id}/image",
        "transaction_id": tx.id,
        "amount": total,
        "merchant": merchant,
    }


@router.get("/receipts")
def list_receipts(db: Session = Depends(get_db)):
    rows = db.query(Receipt).order_by(Receipt.uploaded_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "uploaded_at": r.uploaded_at,
            "ocr_text": r.ocr_text[:200],
            "image_url": f"/api/receipts/{r.id}/image",
        }
        for r in rows
    ]


@router.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    image_path = os.path.join(UPLOAD_DIR, f"{receipt.id}.png")
    if os.path.exists(image_path):
        os.remove(image_path)
    db.query(Transaction).filter(Transaction.receipt_id == receipt_id).delete()
    db.delete(receipt)
    db.commit()
    return {"deleted": receipt_id}


@router.get("/receipts/{receipt_id}/image")
def receipt_image(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    image_path = os.path.join(UPLOAD_DIR, f"{receipt.id}.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/png")