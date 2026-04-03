from datetime import datetime
from pydantic import BaseModel, ConfigDict, PrivateAttr, computed_field
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

    _org_code: str = PrivateAttr(default="YKG")
    _mod_prefix: str = PrivateAttr(default="LAB")

    @computed_field
    @property
    def display_id(self) -> str:
        """Standardized: YKG-LAB-0001"""
        return f"{self._org_code}-{self._mod_prefix}-{str(self.id).zfill(4)}"

    model_config = ConfigDict(from_attributes=True)


class LabResultStatus(str, Enum):
    received = "Received"
    verified = "Verified"
    printed = "printed"
    pending = "pending"
