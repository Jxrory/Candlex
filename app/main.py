import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import get_pool, close_pool
from app.router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CandleX starting up")
    await get_pool()
    yield
    await close_pool()
    logger.info("CandleX shut down")


app = FastAPI(title="CandleX", lifespan=lifespan)
app.include_router(router)
