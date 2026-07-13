"""
Punto de entrada principal de la aplicación FastAPI.

Configura la instancia de FastAPI, middleware CORS, eventos de ciclo de vida
e incluye los routers de la API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import easyocr
import sys
from unittest.mock import MagicMock

# MOCK MATPLOTLIB: Evitar error de compatibilidad C-extension en Python 3.14 Alpha
# Supervision importa matplotlib solo para colores, que no estamos usando.
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.api.v1 import plates
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.university_persons import router as university_persons_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestiona el ciclo de vida de la aplicación.

    Al iniciar: precarga el modelo de EasyOCR para evitar latencia en la
    primera solicitud.
    Al finalizar: limpieza de recursos.
    """
    # --- Inicio: precargar el lector de EasyOCR ---
    # EasyOCR descarga modelos en la primera ejecución; hacerlo aquí
    # garantiza que la primera request no sufra latencia extra.
    app.state.ocr_reader = easyocr.Reader(
        ["es", "en"],  # Español e inglés para mejor cobertura de caracteres
        gpu=False,
        verbose=False,
    )
    yield
    # --- Cierre: liberar recursos ---
    del app.state.ocr_reader


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API para la detección y lectura de placas vehiculares bolivianas "
        "usando visión por computadora (Roboflow + EasyOCR)."
    ),
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# --- Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Routers ---
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
