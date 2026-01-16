from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Any, Dict, List

from app.schemas.lab import PatientOut
from app.schemas.visit import PaymentMode


class PrefferedModeOfAppointment(str, Enum):
    in_person = "in_person"
    video = "video"
    phone = "phone"


class AppointmentStatus(str, Enum):
    cancelled = "cancelled"
    completed = "completed"
    upcoming = "upcoming"
    in_progress = "in_progress"


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str | None

    model_config = ConfigDict(from_attributes=True)


class AppointmenCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_at: str
    start_time: str
    end_time: str
    preffered_mode: PrefferedModeOfAppointment
    reason: str | None = None
    notes: str | None = None
    mode_of_payment: PaymentMode
    test_ids: List[int]


class TestResponse(BaseModel):
    id: int
    name: str
    # test_category_id: int
    # default_analyzer_id: int
    price_ghs: Decimal

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    patient: PatientOut
    doctor: UserResponse
    # created_at: datetime | None
    appointment_at: datetime
    start_time: time
    end_time: time
    preffered_mode: PrefferedModeOfAppointment | None
    reason: str | None
    notes: str | None
    status: str | None
    mode_of_payment: PaymentMode
    tests: List[TestResponse] = []
    # created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CreateAppointment(BaseModel):
    patient_id: int
    doctor_id: int
    test_type: int
    preffered_mode: PrefferedModeOfAppointment
    start_time: time
    end_time: time
    mode_of_payment: PaymentMode
    reason: str | None
    quick_notes: str | None
    status: AppointmentStatus | None = AppointmentStatus.upcoming

    model_config = ConfigDict(from_attributes=True)


class TestCategoryResponse(BaseModel):
    id: int
    category_name: str
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)
