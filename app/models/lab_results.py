# from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from sqlalchemy.sql import func
# from app.db.base import Base

# class LabResult(Base):
#     __tablename__ = "lab_results"
#     id: Mapped[int] = mapped_column(primary_key=True)

#     order_item_id: Mapped[int] = mapped_column(ForeignKey("lab_order_items.id"), index=True)
#     analyzer_message_id: Mapped[int | None] = mapped_column(ForeignKey("analyzer_messages.id"), nullable=True)

#     analyte_code: Mapped[str] = mapped_column(String(80), index=True)  # e.g. GLU, WBC, Na
#     value: Mapped[str | None] = mapped_column(String(120), nullable=True)
#     unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
#     flags: Mapped[str | None] = mapped_column(String(40), nullable=True)
#     ref_range: Mapped[str | None] = mapped_column(String(80), nullable=True)

#     raw_record: Mapped[str | None] = mapped_column(Text, nullable=True)

#     created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

#     order_item = relationship("LabOrderItem")

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base

class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_item_id: Mapped[int] = mapped_column(ForeignKey("lab_order_items.id"), index=True)
    analyzer_message_id: Mapped[int | None] = mapped_column(ForeignKey("analyzer_messages.id"), nullable=True)

    # Explicit foreign keys to users
    entered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    analyte_code: Mapped[str] = mapped_column(String(80), index=True)  # e.g. GLU, WBC, Na
    value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    flags: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ref_range: Mapped[str | None] = mapped_column(String(80), nullable=True)

    raw_record: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("LabOrderItem")

    # Relationships with explicit foreign_keys
    entered_by_user = relationship(
        "User",
        foreign_keys=[entered_by_user_id],
        back_populates="entered_results"
    )
    verified_by_user = relationship(
        "User",
        foreign_keys=[verified_by_user_id],
        back_populates="verified_results"
    )