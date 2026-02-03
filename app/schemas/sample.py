from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class SampleCondition(str, Enum):
    fasting = "fasting"
    postpranial = "postpranial"
    preserved_in_EDTA = "preserved_in_EDTA"


class SampleCreate(BaseModel):
    sample_type: int
    appointment_id: int
    patient_id: int
    test_requested: List[int]
    priority: Optional[str] = None
    storage_location: Optional[str] = None
    # TODO; get from authenticated user
    # collector_id: Optional[int] = None
    collection_site: Optional[str] = None
    sample_condition: Optional[SampleCondition] = SampleCondition.fasting
    status: Optional[str] = None


class SampleResponse(BaseModel):
    sample_type: int
    appointment_id: int
    patient_id: int
    test_requested: List[int]
    priority: Optional[str] = None
    storage_location: Optional[str] = None
    # TODO; get from authenticated user
    # collector_id: Optional[int] = None
    collection_site: Optional[str] = None
    sample_condition: Optional[str] = None
    status: Optional[str] = None


class SampleCategoryCreate(BaseModel):
    category_name: str


class SampleCategoryResponse(BaseModel):
    id: int
    category_name: str

    class Config:
        from_attributes = True
