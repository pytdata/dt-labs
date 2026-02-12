from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Enum
from app.schemas.appointment import UserResponse
from app.schemas.sample import SampleResponse


class LabResultResponse(BaseModel):
    id: int
    status: str
    source: str
    results: dict | None
    received_at: datetime

    sample: SampleResponse | None
    # order_item: LabOrderItemResponse
    # analyzer: AnalyzerResponse | None
    entered_by_user: UserResponse | None
    verified_by_user: UserResponse | None

    model_config = ConfigDict(from_attributes=True)


class LabResultStatus(str, Enum):
    received = "Received"
    verified = "Verified"
    printed = "printed"
    pending = "pending"
