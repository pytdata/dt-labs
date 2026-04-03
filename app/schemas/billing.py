from datetime import datetime

from pydantic import BaseModel, PrivateAttr, computed_field
from typing import List, Optional
from decimal import Decimal


class PaymentCreate(BaseModel):
    amount: Decimal
    method: str  # cash | momo | card
    reference: Optional[str] = None
    # List of InvoiceItem IDs the receptionist checked in the modal
    test_ids_to_clear: List[int] = []
    description: Optional[str] = ""


class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    transaction_date: datetime
    method: str

    class Config:
        from_attributes = True


class BillingItemRead(BaseModel):
    id: int
    test_name: str
    price_at_booking: Decimal
    is_paid: bool

    class Config:
        from_attributes = True


class InvoiceStatusRead(BaseModel):
    status: str
    balance: Decimal
    amount_paid: Decimal

    class Config:
        from_attributes = True


class AppointmentSummaryRead(BaseModel):
    id: int
    appointment_at: datetime
    invoice: InvoiceStatusRead | None

    class Config:
        from_attributes = True


class PatientSummaryRead(BaseModel):
    id: int
    first_name: str
    surname: str
    patient_no: str
    profile_image: str | None

    class Config:
        from_attributes = True


class BillingRead(BaseModel):
    id: int
    bill_no: str
    total_billed: Decimal
    created_at: datetime
    patient: PatientSummaryRead
    appointment: AppointmentSummaryRead
    items: list[BillingItemRead]

    # Matching your design pattern exactly
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="BIL")

    @computed_field
    @property
    def display_id(self) -> str:
        """
        Generates the standard format: YKG-BIL-0074
        Note: Using zfill(4) to match your Appointment pattern
        """
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    class Config:
        from_attributes = True
