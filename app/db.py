from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.configurations.config import POSTGRES_DSN_ASYNC

engine = create_async_engine(POSTGRES_DSN_ASYNC, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def init_models() -> None:
    # Import models so metadata is populated
    from app.models import ad  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 