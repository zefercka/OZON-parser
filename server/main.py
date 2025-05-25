from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.src.ozon.controller import app as ozon_controller

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ozon_controller)