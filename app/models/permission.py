from sqlalchemy import ForeignKey, String, JSON, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.db.base import Base

# Association Table for Many-to-Many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True
    )  # e.g., "Medical Officer"
    slug: Mapped[str] = mapped_column(
        String(50), unique=True
    )  # e.g., "medical_officer"
    description: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    users: Mapped[List["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(50))  # e.g., "patients", "billing"
    action: Mapped[str] = mapped_column(String(20))  # e.g., "read", "write", "delete"

    roles: Mapped[List["Role"]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self):
        return f"{self.resource}:{self.action}"
