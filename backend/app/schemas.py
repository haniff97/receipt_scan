from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransactionBase(BaseModel):
    date: datetime
    amount: float
    merchant: str
    category: str
    description: str = ""


class TransactionCreate(TransactionBase):
    lhdn_relief: str | None = None


class TransactionOut(TransactionBase):
    id: int
    receipt_id: int | None = None
    lhdn_relief: str | None = None
    lhdn_confidence: float | None = None
    tax_year: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ReceiptOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    ocr_text: str
    transactions: list[TransactionOut]

    model_config = ConfigDict(from_attributes=True)


class ReceiptCreateResponse(BaseModel):
    id: int
    filename: str
    transactions_created: int
    ocr_text: str
    image_url: str = ""
    transaction_id: int | None = None
    amount: float | None = None
    merchant: str | None = None
    lhdn_relief: str | None = None
    lhdn_confidence: float | None = None