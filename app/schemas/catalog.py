from typing import Optional
from pydantic import BaseModel


class AnalyzerOut(BaseModel):
    id: int
    name: str
    is_active: bool = True
    is_automated: bool = False
    connection_type: str | None = None
    transport_type: str | None = None
    protocol_type: str | None = None
    protocol: str | None = None
    result_format: str | None = None
    tcp_ip: str | None = None
    tcp_port: int | None = None
    serial_port: str | None = None
    baud_rate: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}


class AnalyzerCreate(BaseModel):
    name: str
    is_active: bool = True
    is_automated: bool = False
    connection_type: str = "manual"
    transport_type: str | None = None
    protocol_type: str | None = "hl7"
    result_format: str = "HL7"
    tcp_ip: str | None = None
    tcp_port: int | None = None
    serial_port: str | None = None
    baud_rate: int | None = None
    parity: str | None = None
    stop_bits: int | None = None
    data_bits: int | None = None
    flow_control: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    notes: str | None = None
    patient_id_source: str = "patient_no"
    patient_id_fallbacks: str | None = None


class AnalyzerUpdate(AnalyzerCreate):
    name: str | None = None


class TestOut(BaseModel):
    id: int
    name: str
    department: str | None = None
    price_ghs: float | None = None
    default_analyzer_id: int | None = None
    model_config = {"from_attributes": True}


class TestCategoryCreate(BaseModel):
    category_name: str
    category_description: str


class TestCategoryResponse(BaseModel):
    id: int
    category_name: str
    category_description: str
    added_by_id: Optional[int]

    class Config:
        from_attributes = True