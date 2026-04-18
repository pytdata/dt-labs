from pydantic import BaseModel
from typing import Optional
from pydantic import EmailStr
from enum import Enum


class PrefixUpdate(BaseModel):
    org_identifier: str
    patient: str
    test: str
    appointment: str
    invoice: str
    bill: str
    analyzer: str
    payment: str
    lab: str
    radiology: str


class PrefixRead(PrefixUpdate):
    id: int

    class Config:
        from_attributes = True


class InsuranceType(str, Enum):
    public = "public"
    private = "private"


class InsuranceBase(BaseModel):
    name: str
    type: InsuranceType = InsuranceType.private
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class InsuranceCreate(InsuranceBase):
    pass


class InsuranceResponse(InsuranceBase):
    id: int

    class Config:
        from_attributes = True
