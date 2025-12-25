import asyncio
from app.db.session import AsyncSessionLocal
from app.services.seed_service import seed_from_json

async def main():
    async with AsyncSessionLocal() as session:
        await seed_from_json(session)

if __name__ == "__main__":
    asyncio.run(main())