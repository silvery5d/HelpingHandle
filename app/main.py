import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)

import app.models  # noqa: F401, E402 — ensure all models registered before create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Agent capability registry and demand matching platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


from app.routers import agents, capabilities, demands, search, status, verification, wallet
from app.web.views import router as web_router

app.include_router(agents.router)
app.include_router(status.router)
app.include_router(capabilities.router)
app.include_router(demands.router)
app.include_router(search.router)
app.include_router(wallet.router)
app.include_router(verification.router)
app.include_router(web_router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
