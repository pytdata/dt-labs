from fastapi import Depends, HTTPException, Request

# from jose import jwt, JWTError
import jwt
from jwt import PyJWTError
from sqlalchemy import select
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.users import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email: str = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
