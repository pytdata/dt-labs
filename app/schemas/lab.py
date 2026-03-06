from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional
from pydantic import ConfigDict

from app.schemas.test_templates import TestResponse


class PatientCreate(BaseModel):
    first_name: str
    surname: str
    other_names: str | None = None
    sex: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    age: int

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
    # last_visit_date: datetime | None

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


class QueuePatient(BaseModel):
    id: int
    full_name: str
    patient_no: str
    age: int
    sex: str
    model_config = ConfigDict(from_attributes=True)


class QueuePhlebotomy(BaseModel):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QueueAppointment(BaseModel):
    id: int
    patient: QueuePatient
    # Add this! It can be None if the session hasn't started yet
    phlebotomy: Optional[QueuePhlebotomy] = None
    model_config = ConfigDict(from_attributes=True)


class QueueOrder(BaseModel):
    id: int
    appointment: QueueAppointment
    model_config = ConfigDict(from_attributes=True)


class LabQueueResponse(BaseModel):
    id: int
    status: str
    test: TestResponse  # Use your existing TestResponse
    order: QueueOrder

    model_config = ConfigDict(from_attributes=True)


class TestResponse(BaseModel):
    id: int
    name: str
    sample_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LabOrderItemResponse(BaseModel):
    id: int  # This is the LabOrderItem Primary Key
    status: str
    stage: str
    test: TestResponse  # Nested test object

    model_config = ConfigDict(from_attributes=True)
