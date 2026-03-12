from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TestResponse(BaseModel):
    id: int
    name: str
    # department: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TestTemplatesResponse(BaseModel):
    id: int
    test_name: str
    result: float | None
    unit: str
    min_reference_range: float | None
    max_reference_range: float | None
    comment: str | None = None
    created_on: datetime
    short_code: str | None

    test: TestResponse

    model_config = ConfigDict(from_attributes=True)


class TestTemplateCreate(BaseModel):
    test_id: int
    test_name: str
    unit: str
    # result: float | None
    short_code: str | None
    min_reference_range: float | None
    max_reference_range: float | None
    # comment: str | None = None
    # created_on: datetime | None
    model_config = ConfigDict(from_attributes=True)


class TestTemplateUpdate(BaseModel):
    result: Optional[float] = None
    unit: Optional[str] = None
    min_reference_range: Optional[float] = None
    max_reference_range: Optional[float] = None
    comment: Optional[str] = None


# class TestTemplateResponse(BaseModel):
#     id: int
#     test_id: int
#     test_name: str
#     result: float
#     unit: str
#     min_reference_range: float
#     max_reference_range: float
#     comment: str | None

#     class Config:
#         from_attributes = True
