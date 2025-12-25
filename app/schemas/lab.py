from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict

class PatientCreate(BaseModel):
    first_name: str
    surname: str
    other_names: str | None = None
    sex: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None

    patient_type: str = Field(default="cash", pattern="^(cash|insurance)$")
    insurance_company_id: int | None = None
    insurance_member_id: str | None = None

    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_relation: str | None = None

class PatientOut(PatientCreate):
    id: int
    patient_no: str
    full_name: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class LabOrderCreate(BaseModel):
    patient_id: int
    test_ids: list[int]

class LabOrderOut(BaseModel):
    id: int
    patient_id: int
    status: str
    model_config = {"from_attributes": True}


class SampleCollectIn(BaseModel):
    collected_by_user_id: int | None = None
    collected_at: datetime | None = None
    note: str | None = None


class SampleOut(BaseModel):
    order_id: int
    sample_id: str
    model_config = {"from_attributes": True}


class LabResultIn(BaseModel):
    results: Dict[str, Any]
    comments: str | None = None
    status: str = Field(default="received", pattern="^(received|verified)$")


class LabResultOut(BaseModel):
    id: int
    order_item_id: int
    status: str
    sample_id: str | None = None
    results: Dict[str, Any] | None = None
    comments: str | None = None
    verified_at: datetime | None = None
    model_config = {"from_attributes": True}
