from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.lab import PatientOut


class PaymentFilterParams(BaseModel):
    invoice_id: int | None = None
    patient_id: int | None = None
    method: str | None = None


class PatientMiniResponse(BaseModel):
    id: int
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class UserMiniResponse(BaseModel):
    id: int
    full_name: Optional[str] = None

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

    model_config = {"from_attributes": True}


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

    model_config = ConfigDict(from_attributes=True)


class GenerateInvoicePayload(BaseModel):
    order_id: int
    payment_mode: str | None = None
    notes: str | None = None
