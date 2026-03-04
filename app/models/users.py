from enum import Enum
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.lab import LabResult
from app.schemas.staff import Gender, StaffRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default=StaffRole.Receptionist)
    phone_number: Mapped[str | None] = mapped_column(default="", nullable=True)
    gender: Mapped[str | None] = mapped_column(default=Gender.MALE, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    entered_results: Mapped[list["LabResult"]] = relationship(
        "LabResult",
        foreign_keys="LabResult.entered_by_user_id",
        back_populates="entered_by_user",
    )

    verified_results: Mapped[list["LabResult"]] = relationship(
        "LabResult",
        foreign_keys="LabResult.verified_by_user_id",
        back_populates="verified_by_user",
    )

    # relationships
    visits = relationship("Visit", back_populates="doctor")

    def __repr__(self) -> str:
        return f"{self.email!r} {self.full_name!r} {self.gender!r}"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    # relationships
    visits = relationship("Visit", back_populates="department")
