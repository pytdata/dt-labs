from datetime import date, datetime
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


class VisitResponse(BaseModel):
    id: int
    visit_date: datetime
    reason: str | None
    status: VisitStatus
    patient: PatientMini
    department: DepartmentMini
    doctor: DoctorMini

    model_config = ConfigDict(from_attributes=True)
