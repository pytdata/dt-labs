from pydantic import BaseModel
from typing import List, Dict, Optional


class RoleCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    # This matches: {"patients": ["read", "write"], "billing": ["read"]}
    access_map: Dict[str, List[str]]


class PermissionSchema(BaseModel):
    resource: str
    action: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    slug: str
    permissions: List[PermissionSchema]

    class Config:
        from_attributes = True
