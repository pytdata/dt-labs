from pydantic import BaseModel
from typing import Optional


class PrefixUpdate(BaseModel):
    org_identifier: str
    patient: str
    test: str
    appointment: str
    invoice: str
    bill: str
    analyzer: str
    payment: str
    lab: str
    radiology: str


class PrefixRead(PrefixUpdate):
    id: int

    class Config:
        from_attributes = True
