from pydantic import BaseModel

class AnalyzerOut(BaseModel):
    id: int
    name: str
    protocol: str | None = None
    connection_type: str | None = None
    host: str | None = None
    port: str | None = None
    model_config = {"from_attributes": True}

class TestOut(BaseModel):
    id: int
    name: str
    department: str | None = None
    price_ghs: float | None = None
    default_analyzer_id: int | None = None
    model_config = {"from_attributes": True}
