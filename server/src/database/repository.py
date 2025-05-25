from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

T = TypeVar("T", bound=DeclarativeMeta)
class BaseRepository(Generic[T]):
    model: Type[T]

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, **filter) -> Optional[T]:
        query = select(cls.model).filter_by(**filter).limit(1)
        result = await session.execute(query)
        return result.scalars().one_or_none()
    
    @classmethod
    async def add(cls, session: AsyncSession, **data) -> None:
        new_item = cls.model(**data)
        
        session.add(new_item)
    
    @classmethod
    async def update(cls, session: AsyncSession, id: int, **data) -> None:
        query = update(cls.model).where(cls.model.id == id).values(**data)
        await session.execute(query)
        
