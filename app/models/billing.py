from __future__ import annotations

from sqlalchemy import String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

# from app.models.lab import Appointment
# from app.models.users import User


class Invoice(Base):
    """Invoices are created at booking time.

    Supports partial payments (many payments per invoice).
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), index=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_orders.id"), nullable=True, index=True
    )

    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    # what user paid
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="unpaid"
    )  # unpaid|partial|paid

    payment_mode: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # cash|momo
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    patient = relationship("Patient")
    order = relationship("LabOrder")

    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    appointment: Mapped["Appointment"] = relationship(back_populates="invoice")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    qty: Mapped[int] = mapped_column(default=1)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2))

    # invoice = relationship("Invoice", backref="items")
    test = relationship("Test")

    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="items",
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    transaction_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    method: Mapped[str] = mapped_column(String(30), default="cash")  # cash|momo
    verified_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(30), default="")
    reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # momo txn id etc
    received_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # This identifies the staff member who confirmed the cash was in hand or Momo was received
    verified_by: Mapped["User"] = relationship(back_populates="verified_payments")
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="payments",
    )
