import asyncio
import json
import logging
from collections.abc import AsyncIterator

from .config import Settings
from .servicio import Servicio, conexion

logger = logging.getLogger(__name__)


def evento(nombre: str, data: dict) -> str:
    return f"event: {nombre}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class Sondeo:
    def __init__(self, servicio: Servicio, settings: Settings):
        self.servicio = servicio
        self.settings = settings
        self._suscriptores: set[asyncio.Queue[str]] = set()
        self._ultima: dict[str, str] = {}
        self._conexion: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def iniciar(self) -> None:
        self._task = asyncio.create_task(self._ciclo())

    async def detener(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _ciclo(self) -> None:
        while True:
            try:
                respuesta = await self.servicio.ultimas()
                for reading in respuesta.sensores:
                    key = f"{reading.actualizado}:{reading.estado}"
                    if self._ultima.get(reading.id) != key:
                        self._ultima[reading.id] = key
                        await self.publicar(evento("lectura", reading.model_dump(mode="json")))
                await self._publicar_conexion(conexion(respuesta.sensores), influx="ok")
            except Exception:
                # Nunca dejar morir la tarea: sin ella no hay tiempo real.
                logger.exception("Error durante el sondeo de sensores")
                self._ultima.clear()
                await self._publicar_conexion("sin_datos", influx="no_disponible")
            await asyncio.sleep(self.settings.sondeo_s)

    async def _publicar_conexion(self, estado: str, influx: str) -> None:
        if self._conexion != estado:
            self._conexion = estado
            await self.publicar(evento("conexion", {"conexion": estado, "influx": influx}))

    async def suscribir(self) -> AsyncIterator[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._suscriptores.add(queue)
        try:
            try:
                inicial = await self.servicio.ultimas()
                for reading in inicial.sensores:
                    yield evento("lectura", reading.model_dump(mode="json"))
                yield evento("conexion", {"conexion": conexion(inicial.sensores), "influx": "ok"})
            except Exception:
                logger.exception("No se pudo obtener el estado inicial del stream")
                yield evento("conexion", {"conexion": "sin_datos", "influx": "no_disponible"})
            while True:
                yield await queue.get()
        finally:
            self._suscriptores.discard(queue)

    async def publicar(self, event: str) -> None:
        for queue in tuple(self._suscriptores):
            await queue.put(event)
