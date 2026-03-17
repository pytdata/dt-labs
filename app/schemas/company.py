from pydantic import BaseModel


class CompanyProfileOut(BaseModel):
    id: int
    name: str
    phone: str | None = None
    address: str | None = None
    email: str | None = None
    slogan: str | None = None
    logo: str | None = None

    model_config = {"from_attributes": True}


class CompanyProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    email: str | None = None
    slogan: str | None = None
    logo: str | None = None
