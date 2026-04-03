from enum import Enum
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    PrivateAttr,
    computed_field,
    field_validator,
)
from typing import Optional


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class StaffRole(str, Enum):
    Receptionist = "receptionist"
    Admin = "admin"
    lab_scientist = "lab_scientist"


class StaffResponse(BaseModel):
    id: int
    full_name: str
    role: str | None
    email: EmailStr
    phone_number: str | None
    gender: Gender | None
    is_active: bool
    avatar: str

    # Standardized Staff Prefix
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="STF")

    @field_validator("role", mode="before")
    @classmethod
    def transform_role(cls, v):
        # This converts the Role DB object into the string name for the JSON
        if hasattr(v, "name"):
            return v.name
        return v

    @computed_field
    @property
    def display_id(self) -> str:
        """Formatted Staff ID: e.g., YKG-STF-0005"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class StaffCreate(BaseModel):
    full_name: str
    role: str  # This will receive the role slug from the frontend
    email: EmailStr
    phone_number: str
    gender: Gender
    password: str

    model_config = ConfigDict(from_attributes=True)


class StaffUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)
