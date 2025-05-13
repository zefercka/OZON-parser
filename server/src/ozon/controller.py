from fastapi import APIRouter
from server.src.database import AsyncDbSession

app = APIRouter(
    prefix="/ozon",
)


@app.post("/check")
async def check(
    session: AsyncDbSession 
):
    return "Hello world"