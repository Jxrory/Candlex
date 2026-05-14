from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import get_pool, close_pool
from app.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="CandleX", lifespan=lifespan)
app.include_router(router)
