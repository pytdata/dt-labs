from enum import Enum
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# from app.models.billing import Payment
from app.models.lab import Appointment, LabResult
from app.models.permission import Role
from app.schemas.staff import Gender, StaffRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # FK to the new Roles table
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id"))

    phone_number: Mapped[str | None] = mapped_column(default="", nullable=True)
    gender: Mapped[str | None] = mapped_column(default="MALE", nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    profile_picture: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- RBAC RELATIONSHIP ---
    role: Mapped[Optional["Role"]] = relationship(
        "Role", back_populates="users", lazy="selectin"
    )

    entered_results: Mapped[List["LabResult"]] = relationship(
        "LabResult",
        foreign_keys="LabResult.entered_by_user_id",
        back_populates="entered_by_user",
    )

    verified_results: Mapped[List["LabResult"]] = relationship(
        "LabResult",
        foreign_keys="LabResult.verified_by_user_id",
        back_populates="verified_by_user",
    )

    appointments_booked: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        foreign_keys="[Appointment.created_by_user_id]",
        back_populates="created_by_user",
    )

    verified_payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="verified_by"
    )

    visits: Mapped[List["Visit"]] = relationship("Visit", back_populates="doctor")

    def __repr__(self) -> str:
        return f"<{self.email!r} {self.full_name!r} Role ID: {self.role_id}>"

    def has_permission(self, resource: str, action: str) -> bool:
        """
        Checks if the user's role has a specific permission.
        Admins bypass all checks.
        """
        if not self.role:
            return False

        # 1. THE ADMIN OVERRIDE
        # If the role slug is 'admin', allow everything
        if self.role.slug == "admin":
            return True

        # 2. STANDARD PERMISSION CHECK
        if not self.role.permissions:
            return False

        return any(
            p.resource == resource and p.action == action for p in self.role.permissions
        )

    @property
    def avatar(self) -> str:
        if self.profile_picture:
            return self.profile_picture
        return "/static/img/defaults/default-user-icon.jpeg"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    # relationships
    visits = relationship("Visit", back_populates="department")
