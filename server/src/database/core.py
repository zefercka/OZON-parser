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
    
    def dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


async def get_db():
    async with SessionLocal() as session:
        try:
            transaction = session.begin()
            await transaction.start()
            yield session
            await transaction.commit()
        except Exception as err:
            await transaction.rollback()
            raise err
        finally:
            await session.close()
            
        

AsyncDbSession = Annotated[AsyncSession, Depends(get_db)]
            