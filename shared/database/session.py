
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

DATABASE_URL = settings.async_database_url
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
	bind=engine,
	autocommit=False,
	autoflush=False,
	expire_on_commit=False,
	class_=AsyncSession,
)


async def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		await db.close()
