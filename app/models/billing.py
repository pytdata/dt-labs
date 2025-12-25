from __future__ import annotations

from sqlalchemy import String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Invoice(Base):
    """Invoices are created at booking time.

    Supports partial payments (many payments per invoice).
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("lab_orders.id"), nullable=True, index=True)

    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid|partial|paid

    payment_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)  # cash|momo
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient")
    order = relationship("LabOrder")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    qty: Mapped[int] = mapped_column(default=1)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2))

    invoice = relationship("Invoice", backref="items")
    test = relationship("Test")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    method: Mapped[str] = mapped_column(String(30), default="cash")  # cash|momo
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)  # momo txn id etc
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", backref="payments")
    verified_by = relationship("User")
