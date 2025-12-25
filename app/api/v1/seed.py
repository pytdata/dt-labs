# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db.session import get_db
# from app.services.seed_service import seed_from_json

# router = APIRouter()

# @router.post("/seed")
# async def seed(db: AsyncSession = Depends(get_db)):
#     await seed_from_json(db)
#     return {"status":"seeded"}


from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.seed_service import seed_from_json

router = APIRouter()

@router.post("/seed")
async def run_seed(db: AsyncSession = Depends(get_db)):
    await seed_from_json(db)
    return {"status": "Seeded successfully"}

