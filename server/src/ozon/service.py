import asyncio
import re

from sqlalchemy.ext.asyncio import AsyncSession

from server.src.ai.preprocessing import Model
from server.src.dependency.exceptions import ItemNotFound, UnknownUrlTypeError
from server.src.ozon.dependency import get_id_from_url
from server.src.ozon.ozon_item_parser import parser
from server.src.ozon.repository import OzonItemRepository
from server.src.ozon.schema import CheckUrl, Feedback, OzonItem

preprocessing_model = Model()
URL_PATTERN = r"^www\.ozon\.ru/product/[a-zA-Z0-9\-]+-\d+/*"


async def check_item_by_url(session: AsyncSession, url: CheckUrl) -> bool:
    url: str = url.url
    url = re.sub("https://", '', url)
    
    print(url)
    if not re.match(URL_PATTERN, url):
        raise UnknownUrlTypeError
    
    url = url.split("?")[0]
    url = re.sub("www.ozon.ru", '', url)
    
    id_ = get_id_from_url(url)
    
    item = await OzonItemRepository.find_one_or_none(session, id=id_)
    
    if item:    
        ozon_item = OzonItem.model_validate(
            {
                "id": item.id,
                "title": item.title,
                "url": f"www.ozon.ru{item.url}",
                "price": item.price,
                "image": item.image,
                "authors": item.author if item.author else [""],
                "is_fake": item.is_fake_model,
                "description": item.description if item.description else "",
            }
        )
        
        return ozon_item
    
    data = await parser(
        session=session,
        url=url
    )
    
    result = await asyncio.to_thread(
        preprocessing_model.preprocessing, data
    )
    data["is_fake_model"] = result
    
    await OzonItemRepository.add(session, **data)
    
    ozon_item = OzonItem.model_validate(
        {
            "id": data["id"],
            "title": data["title"],
            "url": f"www.ozon.ru{data["url"]}",
            "price": data["price"],
            "image": data["image"],
            "authors": data["author"] if "author" in data else [""],
            "is_fake": data["is_fake_model"],
            "description": data["description"] if "description" in data else "",
        }
    )
    
    return ozon_item


async def add_user_decision(
    session: AsyncSession,
    item_id: int,
    feedback: Feedback
) -> None:
    item = await OzonItemRepository.find_one_or_none(
        session, id=item_id
    )
    
    if not item:
        raise ItemNotFound

    if feedback.agree is True:
        await OzonItemRepository.increment_agree(session, item_id)
    else:
        await OzonItemRepository.increment_disagree(session, item_id)
