import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..deepseek import enhance_ocr
from ..database import get_db
from ..models import Receipt, Transaction
from ..schemas import ReceiptCreateResponse
from ..ocr import ocr_image, parse_receipt

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
    try:
        text = ocr_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    parsed = parse_receipt(text)

    ai = enhance_ocr(text)
    if ai and ai.get("total"):
        total = float(ai["total"])
        merchant = ai.get("merchant") or "Unknown"
        category = ai.get("category") or category
        try:
            tx_date = datetime.fromisoformat(ai["date"]) if ai.get("date") else datetime.utcnow()
        except (ValueError, TypeError):
            tx_date = datetime.utcnow()
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
        tx_date = parsed["date"] or datetime.utcnow()

    receipt = Receipt(filename=file.filename or "receipt.png", ocr_text=text)
    db.add(receipt)
    db.flush()

    ext = os.path.splitext(receipt.filename)[1] or ".png"
    image_path = os.path.join(UPLOAD_DIR, f"{receipt.id}{ext}")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

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

    return {
        "id": receipt.id,
        "filename": receipt.filename,
        "transactions_created": 1,
        "ocr_text": text[:500],
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


@router.get("/receipts/{receipt_id}/image")
def receipt_image(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    ext = os.path.splitext(receipt.filename)[1] or ".png"
    image_path = os.path.join(UPLOAD_DIR, f"{receipt.id}{ext}")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/png")