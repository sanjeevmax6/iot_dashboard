from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, chat, data, logs, machines
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting, log level is %s", settings.log_level.upper())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables are ready")
    yield
    await engine.dispose()
    logger.info("Application shutting down, database connections are closed")


app = FastAPI(
    title="IoT Maintenance Insight Dashboard",
    description="AI-powered manufacturing floor maintenance predictor.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router, prefix="/api")
app.include_router(machines.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}
