from sqlalchemy.ext.asyncio import AsyncSession

from server.src.database.repository import BaseRepository
from server.src.ozon.model import OzonItem, OzonSeller


class OzonItemRepository(BaseRepository[OzonItem]):
    model = OzonItem
    
    @classmethod
    async def increment_agree(cls, session: AsyncSession, id: int):
        await cls.update(session, id, agree=cls.model.agree + 1)
    
    @classmethod
    async def increment_disagree(cls, session: AsyncSession, id: int):
        await cls.update(session, id, disagree=cls.model.disagree + 1)
    

class OzonSellerRepository(BaseRepository[OzonSeller]):
    model = OzonSeller