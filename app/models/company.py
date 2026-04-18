import enum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum

from app.db.base import Base


class CompanyProfile(Base):
    __tablename__ = "company_profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255), default="YKG LAB & DIAGNOSTIC CENTER", nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slogan: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo: Mapped[str | None] = mapped_column(nullable=True)

    @property
    def profile_image(self) -> str:
        if self.logo:
            return self.logo
        return "/static/img/defaults/default-company-proifle.jpeg"


class InsuranceType(str, enum.Enum):
    public = "public"
    private = "private"


class InsuranceCompany(Base):
    __tablename__ = "insurance_companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20), default=InsuranceType.private.value)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OrganizationPrefix(Base):
    __tablename__ = "organization_prefixes"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    org_identifier: Mapped[str] = mapped_column(default="YKG", nullable=False)

    # Module Specifics
    patient: Mapped[str] = mapped_column(default="PAT")
    test: Mapped[str] = mapped_column(default="TST")
    appointment: Mapped[str] = mapped_column(default="APT")
    invoice: Mapped[str] = mapped_column(default="INV")
    bill: Mapped[str] = mapped_column(default="BIL")
    analyzer: Mapped[str] = mapped_column(default="ANL")
    payment: Mapped[str] = mapped_column(default="PAY")
    lab: Mapped[str] = mapped_column(default="LAB")
    radiology: Mapped[str] = mapped_column(default="RAD")

    def __repr__(self) -> str:
        return f"<OrganizationPrefix(org={self.org_identifier})>"
