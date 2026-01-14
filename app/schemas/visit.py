from datetime import date, datetime, time
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Any, Dict


class VisitStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    in_progress = "in_progress"


class PatientMini(BaseModel):
    id: int
    patient_no: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class DoctorMini(BaseModel):
    id: int
    full_name: str


class DepartmentMini(BaseModel):
    id: int
    name: str


class PaymentMode(str, Enum):
    cash = "cash"
    insurance = "payment"


class VisitResponse(BaseModel):
    id: int
    visit_date: datetime
    time_of_visit: time | None
    reason: str | None
    status: VisitStatus
    patient: PatientMini
    department: DepartmentMini
    doctor: DoctorMini
    mode_of_payment: PaymentMode | None

    model_config = ConfigDict(from_attributes=True)


class UpdateVisit(BaseModel):
    patient_id: int
    department_id: int
    doctor_id: int
    visit_date: str
    visit_time: str
    reason: str | None
    patient_type: str
    payment_mode: PaymentMode | None


# class VisitResponse(BaseModel):
#     id: int
#     visit_date: datetime
#     reason: str | None
#     status: VisitStatus
#     patient: PatientMini
#     department: DepartmentMini
#     doctor: DoctorMini
#     mode_of_payment: PaymentMode | None

#     model_config = ConfigDict(from_attributes=True)
