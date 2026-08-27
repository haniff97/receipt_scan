from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, default="local-user")
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    amount: Mapped[float] = mapped_column(Float)
    merchant: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    # LHDN tax relief fields
    lhdn_relief: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lhdn_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    receipt_id: Mapped[int | None] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=True
    )
    receipt: Mapped["Receipt | None"] = relationship(back_populates="transactions")


class LhdnLimit(Base):
    __tablename__ = "lhdn_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relief_key: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    cap_amount: Mapped[float] = mapped_column(Float)


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, default="local-user")
    filename: Mapped[str] = mapped_column(String(300))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ocr_text: Mapped[str] = mapped_column(Text, default="")

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )