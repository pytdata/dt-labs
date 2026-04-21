from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, PrivateAttr, computed_field

from app.schemas.lab import PatientOut


# class PaymentFilterParams(BaseModel):
#     invoice_id: int | None = None
#     patient_id: int | None = None
#     method: str | None = None
#     start_date: Optional[date] = None
#     end_date: Optional[date] = None
#     status: Optional[List[str]] = None


class PaymentFilterParams(BaseModel):
    invoice_id: int | None = None
    patient_id: int | None = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = None


class PatientMiniResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    profile_image: str

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="PAT")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class TestMiniResponse(BaseModel):
    id: int
    name: str
    department: Optional[str] = None

    model_config = {"from_attributes": True}


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    test_id: int
    description: str
    unit_price: Decimal
    qty: int
    line_total: Decimal

    test: TestMiniResponse

    model_config = {"from_attributes": True}


class InvoiceMiniResponse(BaseModel):
    id: int
    invoice_no: str
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    status: str
    patient: PatientMiniResponse

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="INV")

    @computed_field
    @property
    def display_id(self) -> str:
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class UserMiniResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    avatar: str

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    method: str
    description: str | None = None
    reference: Optional[str] = None
    transaction_date: datetime
    received_at: datetime

    invoice: InvoiceMiniResponse
    verified_by: Optional[UserMiniResponse] = None

    # Standardized Transaction Prefix
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="TRN")

    @computed_field
    @property
    def display_id(self) -> str:
        """Formatted Transaction ID: YKG-TRN-0001"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    id: int
    invoice_no: str
    total_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    status: str
    created_at: datetime

    patient: PatientOut
    items: list[InvoiceItemResponse]
    payments: list[PaymentResponse]

    # Standardized Prefix Logic
    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="INV")

    @computed_field
    @property
    def display_id(self) -> str:
        """Formatted ID: e.g., YKG-INV-0001"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class GenerateInvoicePayload(BaseModel):
    order_id: int
    payment_mode: str | None = None
    notes: str | None = None
