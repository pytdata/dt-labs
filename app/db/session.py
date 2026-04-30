from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
import ssl

ssl_context = ssl.create_default_context()

engine = create_async_engine(
    settings.DB_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "ssl": ssl_context,
    },
)

print(settings.DB_URL)

# Create a session factory
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
