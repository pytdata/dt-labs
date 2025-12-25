from pydantic import BaseModel, Field
from typing import Any, Literal, Optional, Dict

class ASTMResultIn(BaseModel):
    analyzer_name: str
    sample_id: str
    patient_no: str | None = None
    test_name: str
    parameter: str | None = None
    value: str | float | int | None = None
    unit: str | None = None
    raw: str | None = None

class AnalyzerIngestIn(BaseModel):
    """Generic ingest payload from the analyzer listener service."""
    analyzer_id: Optional[int] = None
    analyzer_name: Optional[str] = None
    format: Literal["ASTM","CSV","XML"] = "ASTM"
    protocol: Optional[str] = None
    order_id: Optional[str] = None
    sample_id: Optional[str] = None
    patient_no: Optional[str] = None
    raw: str = Field(default="")
    parsed: Dict[str, Any] = Field(default_factory=dict)
