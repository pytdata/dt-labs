from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

from app.schemas.appointment import TestResponse


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


# from pydantic import BaseModel
# from typing import List
class SampleCreateRequest(BaseModel):
    patient_id: int
    appointment_id: int
    phlebotomy_id: int | None  # Added to link to the Phlebotomy session
    sample_category_id: int

    # Using Field with defaults to match your DB defaults
    priority: str = Field(default="routine")
    collection_site: str = Field(default="clinic")
    storage_location: str = Field(default="ambient")
    sample_condition: str = Field(default="good")

    # The IDs of the LabOrderItems (tests) this tube fulfills
    test_item_ids: List[int] = Field(..., min_items=1)


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

    model_config = ConfigDict(from_attributes=True)


class SampleItemResponse(BaseModel):
    id: int
    # Ensure TestResponse exists and has 'name'
    test: TestResponse
    status: str

    model_config = ConfigDict(from_attributes=True)


class SampleDetailResponse(BaseModel):
    id: int
    status: str
    collection_date: datetime
    # Add this line here
    phlebotomy_id: Optional[int] = None

    category: Optional[SampleCategoryResponse] = None
    items: List[SampleItemResponse]

    model_config = ConfigDict(from_attributes=True)
