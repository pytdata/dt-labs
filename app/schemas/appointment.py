from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

from app.schemas.lab import PatientOut
from app.schemas.visit import PaymentMode


class PrefferedModeOfAppointment(str, Enum):
    in_person = "in_person"
    # video = "video"
    # phone = "phone"


class AppointmentStatus(str, Enum):
    completed = "completed"
    pending = "pending"


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str | None
    role: str | None
    avatar: str
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


class AppointmentPatchUpdate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    appointment_at: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    mode_of_payment: Optional[str] = None
    test_ids: Optional[List[int]] = None  # If they want to change the tests


class TestCreate(BaseModel):
    name: str = Field(..., min_length=2)
    test_category_id: int
    sample_category_id: Optional[int] = None
    department: Optional[str] = None
    default_analyzer_id: Optional[int] = None
    price_ghs: float = 0.0
    test_duration: str = "24 Hours"
    requires_phlebotomy: bool = True


class TestResponse(BaseModel):
    id: int
    name: str
    # test_category_id: int
    # default_analyzer_id: int
    price_ghs: Decimal

    model_config = ConfigDict(from_attributes=True)


class TestCategoryResponse(BaseModel):
    id: int
    category_name: str
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalyzerResponse(BaseModel):
    id: int
    name: str


class SampleResponseForSettings(BaseModel):
    id: int
    category_name: str


class TestResponseForSettings(TestResponse):
    test_category: Optional[TestCategoryResponse] = None
    default_analyzer: Optional[AnalyzerResponse] = None
    sample_category: Optional[SampleResponseForSettings] = None

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


# 1. New Schema for the individual tests on the bill
class InvoiceItemSummary(BaseModel):
    id: int
    test_id: int
    description: str
    unit_price: Decimal
    is_paid: bool  # This is the visibility toggle for the JS checkbox
    model_config = ConfigDict(from_attributes=True)


# 2. Updated Invoice Summary to include the items
class InvoiceSummary(BaseModel):
    id: int
    invoice_no: str
    status: str
    total_amount: Decimal
    amount_paid: Decimal  # Added this for the modal header
    balance: Decimal
    items: List[InvoiceItemSummary] = []  # <--- THIS IS KEY
    model_config = ConfigDict(from_attributes=True)


class InvoiceSummaryMini(BaseModel):
    id: int
    invoice_no: str | None
    status: str | None
    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    patient: PatientOut
    doctor: UserResponse
    # Add this to track which staff member handled the booking
    # created_by_user: UserResponse | None = None

    appointment_at: datetime
    start_time: time
    end_time: time | None = None
    invoice: InvoiceSummaryMini | None = None

    preffered_mode: PrefferedModeOfAppointment | None = None
    notes: str | None = None
    status: str | None = "pending"

    # Use Decimal for money to match your DB Numeric(12,2)
    total_price: Decimal = Decimal("0.00")
    mode_of_payment: PaymentMode

    # This matches the Relationship in your Appointment model
    tests: List[TestResponse] = []

    model_config = ConfigDict(from_attributes=True)


class LabOrderSummary(BaseModel):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)


# 3. The Main Response
class AppointmentDetailResponse(AppointmentResponse):
    id: int
    patient: PatientOut
    doctor: UserResponse
    # Add this to track which staff member handled the booking
    # created_by_user: UserResponse | None = None

    appointment_at: datetime
    start_time: time
    end_time: time | None = None

    preffered_mode: PrefferedModeOfAppointment | None = None
    notes: str | None = None
    status: str | None = "pending"

    # Use Decimal for money to match your DB Numeric(12,2)
    total_price: Decimal = Decimal("0.00")
    mode_of_payment: PaymentMode

    # This matches the Relationship in your Appointment model
    tests: List[TestResponse] = []

    model_config = ConfigDict(from_attributes=True)

    invoice: Optional[InvoiceSummary] = None
    lab_order: Optional[LabOrderSummary] = None
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


class ManualTestResult(BaseModel):
    test_name_type: str
    test_code: str
    result: list[dict]
    # unit: str
    # ref_range: str
    # comment: str | None
    model_config = ConfigDict(from_attributes=True)


# http://localhost:8000/api/v1/appointments/appointments/4/pending-tests
