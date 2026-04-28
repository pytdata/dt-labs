from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, PrivateAttr, computed_field
from typing import Any, Dict, Optional
from pydantic import ConfigDict

# from app.schemas.test_templates import TestResponse


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
    profile_image: str
    created_at: datetime | None = None
    last_visit_date: datetime | None = None

    # Private attributes for prefixing logic
    _org_code: str = "YKG"
    _mod_prefix: str = "PAT"

    @computed_field
    @property
    def display_id(self) -> str:
        """Formatted ID: e.g., YKG-PAT-0001"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


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

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="PAT")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

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
    appointment_at: datetime

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="APT")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class QueueOrder(BaseModel):
    id: int
    appointment: QueueAppointment
    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    id: int
    category_name: str
    model_config = ConfigDict(from_attributes=True)


class TestResponse(BaseModel):
    id: int
    name: str
    sample_type: Optional[str] = None
    # Ensure this matches the relationship name in your Test model
    test_category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


# class TestResponse(BaseModel):
#     id: int
#     name: str
#     sample_type: Optional[str] = None
#     requires_phlebotomy: bool  # Helpful for the JS logic we wrote
#     # Match the attribute name in your SQLAlchemy model
#     test_category: Optional[CategoryResponse] = None

#     model_config = ConfigDict(from_attributes=True)


class LabQueueResponse(BaseModel):
    id: int
    status: str
    test: TestResponse
    order: "QueueOrder"

    # Private attributes for Lab Item prefix
    _org_code: str = "YKG"
    _mod_prefix: str = "LAB"

    @computed_field
    @property
    def display_id(self) -> str:
        """Formatted Lab Item ID: e.g., YKG-LAB-0001"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class RadiologyResultResponse(BaseModel):
    id: int
    result_value: str
    comments: Optional[str] = None
    status: str
    entered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabResultResponse(BaseModel):
    id: int
    results: Optional[Dict[str, Any]] = None  # JSON data for blood tests
    comments: Optional[str] = None
    status: str
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientResponse(BaseModel):
    id: int
    full_name: str
    # patient_no: str  # Remove or make Optional if not in DB yet
    gender: Optional[str] = "N/A"  # Added Optional and default

    model_config = ConfigDict(from_attributes=True)


class DoctorResponse(BaseModel):
    id: int
    full_name: str
    specialization: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentBaseResponse(BaseModel):
    id: int
    appointment_at: Optional[datetime] = None
    patient: PatientResponse
    doctor: Optional[DoctorResponse] = None
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="APT")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class LabOrderBaseResponse(BaseModel):
    id: int
    # order_no: str | None = None
    # appointment: AppointmentBaseResponse  # Nested Appointment
    patient: Optional[QueuePatient] = None
    appointment: Optional[AppointmentBaseResponse] = None

    # We add private attrs here too in case you want an Order display_id later
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="LAB")

    model_config = ConfigDict(from_attributes=True)


class LabQueueResponse2(BaseModel):
    id: int
    status: str
    stage: str
    entered_at: Optional[datetime] = Field(None, alias="entered_at")
    test: TestResponse
    order: LabOrderBaseResponse
    lab_result: Optional[LabResultResponse] = None

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="RAD")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LabOrderItemResponse(BaseModel):
    id: int
    status: str
    stage: str
    test: TestResponse

    # ADD THESE TWO:
    # Use Optional because a test will usually have one OR the other (or none yet)
    radiology_result: RadiologyResultResponse | None = None
    # lab_result: Optional[LabResultResponse] = None

    model_config = ConfigDict(from_attributes=True)


class RadiologyResultSubmit(BaseModel):
    order_item_id: int
    findings: str  # The long descriptive narrative
    conclusion: Optional[str] = None  # The short "Impression"

    model_config = ConfigDict(from_attributes=True)


class RadiologySubmitRequest(BaseModel):
    order_item_id: int
    findings: str
    conclusion: Optional[str] = None
