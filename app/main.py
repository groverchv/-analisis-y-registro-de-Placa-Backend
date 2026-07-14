"""
Punto de entrada principal de la aplicacion FastAPI.

Configura la instancia de FastAPI, middleware CORS, eventos de ciclo de vida
e incluye los routers de la API.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
EASYOCR_DIR = RUNTIME_DIR / "easyocr"
MPLCONFIG_DIR = RUNTIME_DIR / "matplotlib"
UPLOADS_DIR = PROJECT_ROOT / "uploads"

RUNTIME_DIR.mkdir(exist_ok=True)
EASYOCR_DIR.mkdir(exist_ok=True)
MPLCONFIG_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIG_DIR)

logger = logging.getLogger(__name__)

import easyocr
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import plates
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.university_persons import router as university_persons_router
from app.api.v1.vehicles import router as vehicles_router
from app.config.settings import settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()
sys.modules["matplotlib.colors"] = MagicMock()
sys.modules["matplotlib.patches"] = MagicMock()
sys.modules["matplotlib.figure"] = MagicMock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        app.state.ocr_reader = easyocr.Reader(
            ["es", "en"],
            gpu=False,
            verbose=False,
            model_storage_directory=str(EASYOCR_DIR),
            user_network_directory=str(EASYOCR_DIR),
        )
    except Exception as exc:
        logger.warning("EasyOCR no pudo inicializarse durante el arranque: %s", exc)
        app.state.ocr_reader = None
    yield
    if hasattr(app.state, "ocr_reader"):
        del app.state.ocr_reader


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API para la deteccion y lectura de placas vehiculares bolivianas "
        "usando vision por computadora (Roboflow + EasyOCR)."
    ),
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"],
)
app.include_router(
    dashboard_router,
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    plates.router,
    prefix="/api/v1/plates",
    tags=["Placas"],
)
app.include_router(
    vehicles_router,
    prefix="/api/v1/vehicles",
    tags=["Vehicles"],
)
app.include_router(
    university_persons_router,
    prefix="/api/v1/university-persons",
    tags=["University Persons"],
)
