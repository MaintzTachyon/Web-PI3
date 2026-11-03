import asyncio
import json
import logging
from collections.abc import AsyncIterator

from .config import Settings
from .influx import InfluxUnavailable
from .servicio import Servicio

logger = logging.getLogger(__name__)


class Sondeo:
    def __init__(self, servicio: Servicio, settings: Settings):
        self.servicio = servicio
        self.settings = settings
        self._suscriptores: set[asyncio.Queue[str]] = set()
        self._ultima: dict[str, str] = {}
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
                    encoded = json.dumps(reading.model_dump(mode="json"), ensure_ascii=False)
                    key = f"{reading.actualizado}:{reading.estado}"
                    if self._ultima.get(reading.id) != key:
                        self._ultima[reading.id] = key
                        await self.publicar(f"event: lectura\ndata: {encoded}\n\n")
            except InfluxUnavailable:
                logger.exception("Error durante el sondeo de sensores")
            await asyncio.sleep(self.settings.sondeo_s)

    async def suscribir(self) -> AsyncIterator[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._suscriptores.add(queue)
        try:
            inicial = await self.servicio.ultimas()
            for reading in inicial.sensores:
                yield f"event: lectura\ndata: {json.dumps(reading.model_dump(mode='json'), ensure_ascii=False)}\n\n"
            while True:
                yield await queue.get()
        finally:
            self._suscriptores.discard(queue)

    async def publicar(self, event: str) -> None:
        for queue in tuple(self._suscriptores):
            await queue.put(event)
