# from sqlalchemy import String, Boolean
# from sqlalchemy.orm import Mapped, mapped_column
# from app.db.base import Base

# class User(Base):
#     __tablename__ = "users"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
#     full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
#     password_hash: Mapped[str] = mapped_column(String(255))
#     role: Mapped[str] = mapped_column(String(30), default="admin")  # admin | contact
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# from sqlalchemy import String, Boolean
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from app.db.base import Base

# class User(Base):
#     __tablename__ = "users"

#     id: Mapped[int] = mapped_column(primary_key=True)
#     email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
#     full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
#     password_hash: Mapped[str] = mapped_column(String(255))
#     role: Mapped[str] = mapped_column(String(30), default="admin")  # admin | contact
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True)

#     # Back-populates for clarity
#     entered_results = relationship(
#         "LabResult",
#         foreign_keys="LabResult.entered_by_user_id",
#         back_populates="entered_by_user"
#     )
#     verified_results = relationship(
#         "LabResult",
#         foreign_keys="LabResult.verified_by_user_id",
#         back_populates="verified_by_user"
#     )

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    entered_results = relationship(
        "LabResult",
        foreign_keys="LabResult.entered_by_user_id",
        back_populates="entered_by_user"
    )
    verified_results = relationship(
        "LabResult",
        foreign_keys="LabResult.verified_by_user_id",
        back_populates="verified_by_user"
    )