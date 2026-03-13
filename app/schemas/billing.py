from datetime import datetime

from pydantic import BaseModel
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
