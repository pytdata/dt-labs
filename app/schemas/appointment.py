from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from app.schemas.lab import PatientOut
from app.schemas.visit import PaymentMode


class PrefferedModeOfAppointment(str, Enum):
    in_person = "in_person"
    # video = "video"
    # phone = "phone"


class AppointmentStatus(str, Enum):
    cancelled = "cancelled"
    completed = "completed"
    upcoming = "upcoming"
    in_progress = "in_progress"


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str | None
    role: str | None

    model_config = ConfigDict(from_attributes=True)


class AppointmenCreate(BaseModel):
    patient_id: int
    doctor_id: int
    total_price: Decimal
    # appointment_at: str
    # start_time: str
    # end_time: str
    # preffered_mode: PrefferedModeOfAppointment
    # reason: str | None = None
    notes: str | None = None
    mode_of_payment: PaymentMode
    test_ids: List[int]


class AppointmentUpdate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    appointment_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    mode_of_payment: Optional[str] = None
    total_price: Optional[Decimal] = None
    test_ids: Optional[List[int]] = None


class TestResponse(BaseModel):
    id: int
    name: str
    # test_category_id: int
    # default_analyzer_id: int
    price_ghs: Decimal

    model_config = ConfigDict(from_attributes=True)


class LabResultResponse(BaseModel):
    id: int
    test_no: str | None
    results: dict | None
    received_at: datetime
    comments: str | None
    # test_category_id: int
    # default_analyzer_id: int

    model_config = ConfigDict(from_attributes=True)


class LabResultCreate(BaseModel):
    id: int
    test_no: str
    lab_result: str
    comment: str | None
    unit: str
    # test_category_id: int
    # default_analyzer_id: int

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    patient: PatientOut
    doctor: UserResponse
    # created_at: datetime | None
    appointment_at: datetime
    start_time: time
    end_time: time | None
    preffered_mode: PrefferedModeOfAppointment | None
    notes: str | None
    status: str | None
    total_price: Decimal | None
    mode_of_payment: PaymentMode
    tests: List[TestResponse] = []
    # created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# class CreateAppointment(BaseModel):
#     patient_id: int
#     doctor_id: int
#     test_type: int
#     preffered_mode: PrefferedModeOfAppointment
#     # start_time: time
#     # end_time: time
#     mode_of_payment: PaymentMode
#     reason: str | None
#     quick_notes: str | None
#     status: AppointmentStatus | None = AppointmentStatus.upcoming

#     model_config = ConfigDict(from_attributes=True)


class TestCategoryResponse(BaseModel):
    id: int
    category_name: str
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualTestResult(BaseModel):
    test_name_type: str
    test_code: str
    result: list[dict]
    # unit: str
    # ref_range: str
    # comment: str | None
    model_config = ConfigDict(from_attributes=True)
