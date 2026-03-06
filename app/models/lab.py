from __future__ import annotations

from decimal import Decimal
from sqlalchemy import (
    Numeric,
    String,
    Date,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Time,
)
from sqlalchemy import Enum as SAEnum
from app.models.billing import Invoice
from app.models.enums import LabStage
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from datetime import time

from app.schemas.appointment import AppointmentStatus
from app.schemas.lab_results import LabResultStatus
from app.schemas.visit import PaymentMode
from . import association


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)

    patient_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100))
    other_names: Mapped[str | None] = mapped_column(String(150), nullable=True)

    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_birth: Mapped[Date | None] = mapped_column(Date, nullable=True)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int] = mapped_column()

    # Billing / insurance
    patient_type: Mapped[str] = mapped_column(
        String(20), default="cash"
    )  # cash|insurance
    insurance_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("insurance_companies.id"), nullable=True
    )
    insurance_member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Guardian (optional)
    guardian_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(String(80), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    insurance_company = relationship("InsuranceCompany", lazy="joined")
    lab_orders = relationship(
        "LabOrder",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    visits = relationship(
        "Visit", back_populates="patient", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.other_names or "", self.surname]
        return " ".join([p for p in parts if p]).strip()

    def __repr__(self) -> str:
        return f"{self.full_name!r} {self.age!r} {self.email}"


class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), index=True, nullable=True
    )
    visit_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    time_of_visit: Mapped[time | None] = mapped_column(Time(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    mode_of_payment: Mapped[str] = mapped_column(
        String(15), default="cash", nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patient = relationship("Patient", back_populates="visits")
    department = relationship("Department", back_populates="visits")
    doctor = relationship("User", back_populates="visits")


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0.0, nullable=True
    )
    appointment_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), index=True, default=func.now()
    )
    start_time: Mapped[time] = mapped_column(Time, default=func.current_time())
    end_time: Mapped[time] = mapped_column(Time, nullable=True)
    preffered_mode: Mapped[str] = mapped_column(default="in_person", nullable=True)
    # reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=AppointmentStatus.pending
    )  # scheduled|completed|cancelled
    mode_of_payment: Mapped[str] = mapped_column(default=PaymentMode.cash)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # relationship
    doctor = relationship("User", foreign_keys=[doctor_id])
    tests = relationship(
        "Test", secondary=association.appointment_tests, back_populates="appointments"
    )
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    # Financials & Clinicals
    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="appointment", uselist=False
    )
    lab_order: Mapped["LabOrder"] = relationship(
        "LabOrder", back_populates="appointment", uselist=False
    )
    phlebotomy: Mapped["Phlebotomy"] = relationship(
        "Phlebotomy", back_populates="appointment", uselist=False
    )


class LabOrder(Base):
    __tablename__ = "lab_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    sample_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id"),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )  # pending|in_progress|completed|cancelled

    sample_collected_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    collected_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    sample_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient = relationship("Patient", back_populates="lab_orders")
    collected_by = relationship("User", foreign_keys=[collected_by_user_id])
    appointment = relationship("Appointment", back_populates="lab_order")
    items = relationship(
        "LabOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_orders.id", ondelete="CASCADE"), index=True
    )
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)

    # The Link to Sample
    sample_id: Mapped[int | None] = mapped_column(
        ForeignKey("samples.id", ondelete="SET NULL"), index=True, nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), default="awaiting_sample")
    stage: Mapped[str] = mapped_column(default=LabStage.BOOKING)

    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    entered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    order = relationship("LabOrder", back_populates="items")
    test = relationship("Test")
    # Link back to Sample - notice we use 'items' to match Sample.items
    sample = relationship("Sample", back_populates="items")

    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    entered_by = relationship("User", foreign_keys=[entered_by_user_id])
    result = relationship(
        "LabResult",
        uselist=False,
        back_populates="order_item",
        cascade="all, delete-orphan",
    )


class LabStatusLog(Base):
    """Audit trail for stage/status changes per order item."""

    __tablename__ = "lab_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("lab_order_items.id"), index=True
    )
    from_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(40))
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order_item = relationship("LabOrderItem")
    changed_by = relationship("User")


class AnalyzerMessage(Base):
    __tablename__ = "analyzer_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    analyzer_id: Mapped[int | None] = mapped_column(
        ForeignKey("analyzers.id"), nullable=True
    )
    received_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    raw: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analyzer = relationship("Analyzer")
    results = relationship("LabResult", back_populates="analyzer_message")


class AnalyzerIngestion(Base):
    __tablename__ = "analyzer_ingestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    analyzer_message_id: Mapped[int] = mapped_column(
        ForeignKey("analyzer_messages.id"), index=True
    )
    analyzer_id: Mapped[int | None] = mapped_column(
        ForeignKey("analyzers.id"), nullable=True, index=True
    )
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True, index=True
    )
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_order_items.id"), nullable=True, index=True
    )

    match_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # patient_no|sample_id|heuristic|none
    match_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="unmatched"
    )  # matched|unmatched|error
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analyzer_message = relationship("AnalyzerMessage")
    analyzer = relationship("Analyzer")
    patient = relationship("Patient")
    order_item = relationship("LabOrderItem")


class LabResult(Base):
    __tablename__ = "lab_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("lab_order_items.id"), index=True
    )
    test_no: Mapped[str | None] = mapped_column(nullable=True)
    analyzer_id: Mapped[int | None] = mapped_column(
        ForeignKey("analyzers.id"), nullable=True, index=True
    )
    analyzer_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("analyzer_messages.id"), nullable=True, index=True
    )

    sample_id: Mapped[str | None] = mapped_column(
        ForeignKey("samples.id"), nullable=True
    )

    # who entered/validated (manual or from analyzer)
    entered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    verified_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20), default="analyzer"
    )  # analyzer|manual|import
    status: Mapped[str] = mapped_column(
        String(20), default=LabResultStatus.pending
    )  # received|verified|printed

    results: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # normalized results JSON
    merged_from: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # analyzer ids merged into this record
    raw_format: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # ASTM/CSV/XML
    received_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    verified_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    order_item = relationship("LabOrderItem", back_populates="result")
    analyzer = relationship("Analyzer", back_populates="results")
    analyzer_message = relationship("AnalyzerMessage", back_populates="results")

    sample = relationship("Sample")
    analyzer = relationship("Analyzer")
    analyzer_message = relationship("AnalyzerMessage")
    entered_by_user = relationship("User", foreign_keys=[entered_by_user_id])
    verified_by_user = relationship("User", foreign_keys=[verified_by_user_id])

    def __repr__(self) -> str:
        return f"{self.test_no} {self.results}"


class TestTemplate(Base):
    """
    Creating Test Templates
    """

    __tablename__ = "test_templates"

    id: Mapped[int] = mapped_column(primary_key=True)

    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    test_name: Mapped[str] = mapped_column(String(100))
    short_code: Mapped[str | None] = mapped_column(nullable=True)
    result: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column()
    min_reference_range: Mapped[float | None] = mapped_column(nullable=True)
    max_reference_range: Mapped[float | None] = mapped_column(nullable=True)
    comment: Mapped[str | None] = mapped_column(nullable=True)

    created_on: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationship
    test = relationship("Test", back_populates="templates")

    def __repr__(self) -> str:
        return f"{self.id!r} {self.test_id!r} {self.test_name!r} {self.unit!r}"
