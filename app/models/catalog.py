from enum import Enum
from sqlalchemy import (
    JSON,
    String,
    Text,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Boolean,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func, Time
from datetime import datetime, time

from app.db.base import Base
from app.schemas.sample import SampleCondition
from . import association


class Analyzer(Base):
    __tablename__ = "analyzers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    test_mappings = relationship(
        "AnalyzerTestMapping", back_populates="analyzer", cascade="all, delete-orphan"
    )

    # Dynamic connectivity
    # tcp | serial | manual
    connection_type: Mapped[str] = mapped_column(String(30), default="tcp")

    # What the analyzer emits: ASTM | CSV | XML
    result_format: Mapped[str] = mapped_column(String(20), default="ASTM")
    protocol: Mapped[str] = mapped_column(String(30), default="ASTM")

    # How to match an inbound result to a patient / order in LIS.
    # patient_no: from ASTM P-record (or equivalent)
    # sample_id: from ASTM O-record (specimen/sample id)
    # order_id: from ASTM O-record (order id / placer id, device dependent)
    patient_id_source: Mapped[str] = mapped_column(String(30), default="patient_no")
    # Comma-separated fallbacks to try if the primary source is missing (e.g. "sample_id,order_id")
    patient_id_fallbacks: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # TCP
    tcp_ip: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tcp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Serial
    serial_port: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., COM3 or /dev/ttyUSB0
    baud_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parity: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # none|even|odd
    stop_bits: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1|2
    data_bits: Mapped[int | None] = mapped_column(Integer, nullable=True)  # usually 8
    flow_control: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # none|rtscts|xonxoff

    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TestCategory(Base):
    __tablename__ = "test_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_name: Mapped[str] = mapped_column(String)
    category_description: Mapped[str] = mapped_column(String)
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    date_modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    added_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    modified_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # relationship
    added_by = relationship("User", foreign_keys=[added_by_id])
    modified_by = relationship("User", foreign_keys=[modified_by_id])


class Test(Base):
    __tablename__ = "tests"
    id: Mapped[int] = mapped_column(primary_key=True)

    test_category_id: Mapped[int] = mapped_column(
        ForeignKey("test_categories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_analyzer_id: Mapped[int | None] = mapped_column(
        ForeignKey("analyzers.id"), nullable=True
    )
    price_ghs: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    default_analyzer = relationship("Analyzer")
    analyzer_mappings = relationship(
        "AnalyzerTestMapping", back_populates="test", cascade="all, delete-orphan"
    )
    test_category = relationship("TestCategory")
    appointments = relationship(
        "Appointment", secondary=association.appointment_tests, back_populates="tests"
    )


class TestParameter(Base):
    __tablename__ = "test_parameters"
    __table_args__ = (UniqueConstraint("test_id", "name", name="uq_test_param"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(
        ForeignKey("tests.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_range: Mapped[str | None] = mapped_column(String(100), nullable=True)

    test = relationship("Test", backref="parameters")


class Priority(str, Enum):
    routine = "routine"
    urgent = "urgent"
    stat = "stat"


class StorageLocation(str, Enum):
    fridge = "fridge"
    freezer = "freezer"
    ambient = "ambient"


class CollectionSite(str, Enum):
    hospital = "hospital"
    clinic = "clinic"
    ward = "ward"
    home_service = "home_service"


class SampleStatus(str, Enum):
    collected = "collected"
    in_transit = "in_transit"
    received = "received"
    processed = "processed"
    reported = "reported"


class SampleCategory(Base):
    """
    model to crete and track new sample category or type.
    """

    __tablename__ = "sample_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_name: Mapped[str] = mapped_column()


class Sample(Base):
    """
    Table for saving sample data from the client.
    """

    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type: Mapped[int] = mapped_column(ForeignKey("sample_categories.id"))
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), index=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    test_requested: Mapped[list[int]] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(default=Priority.routine, nullable=True)
    storage_location: Mapped[str] = mapped_column(default=StorageLocation.fridge)
    collection_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    collector_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    collection_site: Mapped[str] = mapped_column(default=CollectionSite.hospital)
    sample_condition: Mapped[str] = mapped_column(
        nullable=True, default=SampleCondition.fasting
    )
    status: Mapped[str] = mapped_column(default=SampleStatus.collected, nullable=True)

    # relationship
    sample_category = relationship("SampleCategory")
    collector = relationship("User")
