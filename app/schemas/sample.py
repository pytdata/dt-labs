from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class SampleCondition(str, Enum):
    fasting = "fasting"
    postpranial = "postpranial"
    preserved_in_EDTA = "preserved_in_EDTA"


# class SampleCreate(BaseModel):
#     phlebotomy_id: int
#     sample_type: int
#     test_ids: list[int]
#     priority: Priority = Priority.routine


class Priority(str, Enum):
    routine = "routine"
    urgent = "urgent"
    stat = "stat"


class SampleCreate(BaseModel):
    phlebotomy_id: int
    sample_type: int
    appointment_id: int
    patient_id: int
    test_ids: List[int]
    priority: Optional[Priority] = None
    storage_location: Optional[str] = None
    # TODO; get from authenticated user
    # collector_id: Optional[int] = None
    collection_site: Optional[str] = None
    sample_condition: Optional[SampleCondition] = SampleCondition.fasting
    status: Optional[str] = None


class SampleTestMiniResponse(BaseModel):
    sample_test_id: int  # association ID
    test_id: int
    name: str

    class Config:
        from_attributes = True


class SampleResponse(BaseModel):
    id: int
    sample_type: str
    priority: str | None
    storage_location: str | None
    collection_site: str | None
    status: str
    appointment_id: int
    patient_id: int
    phlebotomy_id: int | None
    tests: list[SampleTestMiniResponse] = []

    class Config:
        from_attributes = True


class SampleCategoryCreate(BaseModel):
    category_name: str


class SampleCategoryResponse(BaseModel):
    id: int
    category_name: str

    class Config:
        from_attributes = True
