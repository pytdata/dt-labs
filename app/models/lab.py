from sqlalchemy import String, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy import Enum as SAEnum
from app.models.enums import LabStage
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base

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

    # Billing / insurance
    patient_type: Mapped[str] = mapped_column(String(20), default="cash")  # cash|insurance
    insurance_company_id: Mapped[int | None] = mapped_column(ForeignKey("insurance_companies.id"), nullable=True)
    insurance_member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Guardian (optional)
    guardian_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(String(80), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    insurance_company = relationship("InsuranceCompany", lazy="joined")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.other_names or "", self.surname]
        return " ".join([p for p in parts if p]).strip()

class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    visit_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patient = relationship("Patient")

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled|completed|cancelled
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    patient = relationship("Patient")

class LabOrder(Base):
    __tablename__ = "lab_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    sample_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending|in_progress|completed|cancelled

    patient = relationship("Patient")

class LabOrderItem(Base):
    __tablename__ = "lab_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    analyzer_id: Mapped[int | None] = mapped_column(ForeignKey("analyzers.id"), nullable=True)  # chosen per test
    # overall status for LIS
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending|in_progress|completed|cancelled

    # workflow stage (your lab process)
    stage: Mapped[LabStage] = mapped_column(
        SAEnum(LabStage, name="lab_stage"),
        default=LabStage.BOOKING,
    )  # booking|sampling|running|complete|analyzing|printing|ended

    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    external_sample_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # sample/run id used by analyzer

    order = relationship("LabOrder", backref="items")
    test = relationship("Test")
    analyzer = relationship("Analyzer")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    entered_by = relationship("User", foreign_keys=[entered_by_user_id])


class LabStatusLog(Base):
    """Audit trail for stage/status changes per order item."""

    __tablename__ = "lab_status_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("lab_order_items.id"), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(40))
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("LabOrderItem")
    changed_by = relationship("User")

class AnalyzerMessage(Base):
    __tablename__ = "analyzer_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    analyzer_id: Mapped[int | None] = mapped_column(ForeignKey("analyzers.id"), nullable=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analyzer = relationship("Analyzer")

class AnalyzerIngestion(Base):
    __tablename__ = "analyzer_ingestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    analyzer_message_id: Mapped[int] = mapped_column(ForeignKey("analyzer_messages.id"), index=True)
    analyzer_id: Mapped[int | None] = mapped_column(ForeignKey("analyzers.id"), nullable=True, index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("lab_order_items.id"), nullable=True, index=True)

    match_method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # patient_no|sample_id|heuristic|none
    match_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unmatched")  # matched|unmatched|error
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analyzer_message = relationship("AnalyzerMessage")
    analyzer = relationship("Analyzer")
    patient = relationship("Patient")
    order_item = relationship("LabOrderItem")


class LabResult(Base):
    __tablename__ = "lab_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("lab_order_items.id"), index=True)
    analyzer_id: Mapped[int | None] = mapped_column(ForeignKey("analyzers.id"), nullable=True, index=True)
    analyzer_message_id: Mapped[int | None] = mapped_column(ForeignKey("analyzer_messages.id"), nullable=True, index=True)

    # who entered/validated (manual or from analyzer)
    entered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="analyzer")  # analyzer|manual|import
    status: Mapped[str] = mapped_column(String(20), default="received")  # received|verified|printed

    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # normalized results JSON
    raw_format: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ASTM/CSV/XML
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("LabOrderItem")
    analyzer = relationship("Analyzer")
    analyzer_message = relationship("AnalyzerMessage")
    entered_by_user = relationship("User")