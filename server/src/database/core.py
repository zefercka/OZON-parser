from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from server.config import config
from typing import Annotated
from fastapi import Depends


engine = create_async_engine(
    config.DB_URL
)


SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
        

AsyncDbSession = Annotated[AsyncSession, Depends(get_db)]
            