from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import SENSORES_PATH, get_settings
from .influx import InfluxRepository
from .registro import cargar_registro
from .rutas import lecturas, salud, sensores, stream
from .servicio import Servicio
from .simulador import Simulador
from .sondeo import Sondeo


def create_app() -> FastAPI:
    settings = get_settings()
    registro = cargar_registro(SENSORES_PATH)
    repository = Simulador() if settings.modo == "demo" else InfluxRepository(settings)
    servicio = Servicio(registro, repository, settings.modo)
    sondeo = Sondeo(servicio, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await app.state.sondeo.iniciar()
        yield
        await app.state.sondeo.detener()

    app = FastAPI(title="Gemelo Digital L419", version="1.0.0", lifespan=lifespan)
    app.state.servicio = servicio
    app.state.sondeo = sondeo
    if settings.origenes_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.origenes_cors,
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    app.include_router(salud.router, prefix="/api/v1")
    app.include_router(sensores.router, prefix="/api/v1")
    app.include_router(lecturas.router, prefix="/api/v1")
    app.include_router(stream.router, prefix="/api/v1")
    return app


app = create_app()
