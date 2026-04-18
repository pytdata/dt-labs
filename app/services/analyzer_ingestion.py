from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AnalyzerIngestion(Base):
    __tablename__ = "analyzer_ingestion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analyzer_id: Mapped[int] = mapped_column(
        ForeignKey("analyzers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_no: Mapped[str] = mapped_column(
        ForeignKey("lab_test.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    match_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    analyzer_message: Mapped[str] = mapped_column(Text, nullable=False)
    analyzer: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    ingest_status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")

    # Optional helper fields that make later troubleshooting easier.
    raw_message_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    transport_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Relationships assume your existing models expose these back_populates names.
    analyzer_rel = relationship("Analyzer", back_populates="ingestions")
    patient_rel = relationship("Patient", back_populates="analyzer_ingestions")
    lab_test_rel = relationship("LabTest", back_populates="analyzer_ingestions")

    def __repr__(self) -> str:
        return (
            f"AnalyzerIngestion(id={self.id!r}, analyzer_id={self.analyzer_id!r}, "
            f"test_no={self.test_no!r}, ingest_status={self.ingest_status!r})"
        )
