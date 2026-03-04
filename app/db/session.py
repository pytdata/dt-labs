from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

print(settings.DBURL)

engine = create_async_engine(settings.DBURL, echo=False, pool_pre_ping=True)

# Create a session factory
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
