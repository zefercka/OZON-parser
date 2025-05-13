from fastapi import FastAPI

from server.src.ozon.controller import app as ozon_controller

app = FastAPI()

app.include_router(ozon_controller)