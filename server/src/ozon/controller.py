from fastapi import APIRouter

from server.src.database import AsyncDbSession
from server.src.ozon.schema import CheckUrl, Feedback, OzonItem
from server.src.ozon.service import check_item_by_url, add_user_decision

from fastapi import Request

app = APIRouter(
    prefix="/ozon",
)


@app.post("/check")
async def check(
    session: AsyncDbSession,
    url_obj: CheckUrl
) -> OzonItem:
    item = await check_item_by_url(session=session, url=url_obj)
    return item


@app.patch("/feedback/{item_id}")
async def feedback(
    session: AsyncDbSession,
    item_id: int,
    feedback: Feedback
):
    await add_user_decision(session, item_id, feedback)
    return None