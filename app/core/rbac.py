from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.users import User


class PermissionChecker:
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    async def __call__(self, current_user: User = Depends(get_current_user)) -> bool:
        # 1. Check if user has a role
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No role assigned to user"
            )

        # 2. Check for the specific permission
        # Note: permissions are loaded via selectinload in get_current_user
        has_permission = any(
            p.resource == self.resource and p.action == self.action
            for p in current_user.role.permissions
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {self.resource}:{self.action} required",
            )

        return True
