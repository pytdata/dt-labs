from datetime import datetime

from pydantic import BaseModel

from app.models.catalog import CollectionSite
from app.models.enums import PhlebotomyStatus


class PatientResponse(BaseModel):
    id: int
    patient_no: str
    first_name: str
    surname: str

    class Config:
        from_attributes = True


class AppointmentResponse(BaseModel):
    id: int
    patient: PatientResponse

    class Config:
        from_attributes = True


class PhlebotomyResponse(BaseModel):
    id: int
    status: PhlebotomyStatus
    created_at: datetime
    collection_site: CollectionSite
    appointment: AppointmentResponse

    class Config:
        from_attributes = True
