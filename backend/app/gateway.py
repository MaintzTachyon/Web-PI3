"""Fuente de datos: el gateway ESP32 de firmware/gateway_ap (sin MQTT ni InfluxDB).

El gateway recibe los nodos por ESP-NOW, guarda cada mensaje en su flash y los
expone por HTTP en su propia red Wi-Fi (http://192.168.4.1):

  /api/ultimos           último mensaje de cada nodo y hace cuántos segundos llegó
  /api/datos?desde=&max= registros guardados con id > desde (JSONL)
  /api/estado            reloj del gateway (gw_ms), si tiene hora, último id...
  /api/hora?epoch_ms=    le envía la hora (no tiene internet ni NTP)

Este módulo sondea esas rutas, guarda los registros en SQLite (historial y CSV)
y entrega las lecturas con la misma forma que InfluxRepository.
"""
import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .errores import FuenteNoDisponible
from .influx import RANGOS
from .registro import SensorConfig

logger = logging.getLogger(__name__)

# Campos del JSON del gateway que no son mediciones.
META = {"id", "nodo", "mac", "ts", "gw_ms", "uptime_ms", "tipo"}
LOTE = 2000          # registros por pedido a /api/datos
MAX_LOTES = 5        # por ciclo, para no bloquear el sondeo al ponerse al día
MIN_INTERVALO_S = 1.0


class GatewayRepository:
    def __init__(self, settings: Settings, db_path: Path, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._http = httpx.AsyncClient(base_url=settings.gateway_url, timeout=4.0, transport=transport)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS registros ("
            " gw_id INTEGER, nodo INTEGER, tipo TEXT, seq INTEGER, uptime_ms INTEGER, ts_ms INTEGER, msg TEXT,"
            " UNIQUE (nodo, tipo, seq, uptime_ms))"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_serie ON registros (tipo, nodo, ts_ms)")
        self._db.commit()
        # Al reiniciar el backend se sigue desde lo último que ya se guardó.
        self._desde = self._db.execute("SELECT COALESCE(MAX(gw_id), 0) FROM registros").fetchone()[0]
        self._ultimos: dict[tuple[str, int], dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._ultima_sync = 0.0
        self._ok = False

    async def cerrar(self) -> None:
        await self._http.aclose()
        self._db.close()

    async def _get(self, path: str, **params: Any) -> httpx.Response:
        try:
            response = await self._http.get(path, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            self._ok = False
            raise FuenteNoDisponible(f"Gateway no disponible ({self.settings.gateway_url})") from exc

    async def sincronizar(self) -> None:
        """Un ciclo de lectura del gateway; varias llamadas seguidas se agrupan en una."""
        async with self._lock:
            if time.monotonic() - self._ultima_sync < MIN_INTERVALO_S:
                return
            ahora_ms = int(time.time() * 1000)
            estado = (await self._get("/api/estado")).json()
            if not estado.get("hora_ok"):
                # Sin internet el gateway no tiene hora: se la da el servidor.
                await self._get("/api/hora", epoch_ms=ahora_ms)
            self._actualizar_ultimos((await self._get("/api/ultimos")).json(), ahora_ms)
            if estado.get("id_ultimo", 0) < self._desde:
                # Se borró la flash del gateway (/api/borrar): sus ids vuelven a empezar.
                self._desde = 0
            await self._descargar(estado, ahora_ms)
            self._ultima_sync = time.monotonic()
            self._ok = True

    def _actualizar_ultimos(self, filas: list[dict[str, Any]], ahora_ms: int) -> None:
        for fila in filas:
            msg = fila.get("msg") or {}
            hace_s = fila.get("hace_s", -1)
            if hace_s >= 0:
                # Edad medida con el reloj del gateway: no depende de que su hora sea correcta.
                t_ms = ahora_ms - hace_s * 1000
            elif msg.get("ts"):
                t_ms = msg["ts"]          # recuperado de la flash tras un reinicio del gateway
            else:
                continue
            self._ultimos[(str(fila.get("tipo")), int(fila.get("nodo", -1)))] = {
                "fields": {k: v for k, v in msg.items() if k not in META},
                "time": datetime.fromtimestamp(t_ms / 1000, timezone.utc),
            }

    async def _descargar(self, estado: dict[str, Any], ahora_ms: int) -> None:
        for _ in range(MAX_LOTES):
            texto = (await self._get("/api/datos", desde=self._desde, max=LOTE)).text
            lineas = [json.loads(linea) for linea in texto.splitlines() if linea.strip()]
            if not lineas:
                return
            filas = []
            for reg in lineas:
                ts = reg.get("ts")
                if not ts and 0 <= reg.get("gw_ms", -1) <= estado.get("gw_ms", 0):
                    # Sin hora: se estima con millis() del gateway (mismo encendido).
                    ts = ahora_ms - (estado["gw_ms"] - reg["gw_ms"])
                if ts:
                    filas.append((reg.get("id"), reg.get("nodo"), reg.get("tipo"), reg.get("seq"),
                                  reg.get("uptime_ms"), ts, json.dumps(reg)))
            await asyncio.to_thread(self._insertar, filas)
            self._desde = max(self._desde, max(reg.get("id", 0) for reg in lineas))
            if len(lineas) < LOTE:
                return

    def _insertar(self, filas: list[tuple]) -> None:
        self._db.executemany("INSERT OR IGNORE INTO registros VALUES (?, ?, ?, ?, ?, ?, ?)", filas)
        self._db.commit()

    async def ultima_lectura(self, sensor: SensorConfig) -> dict[str, Any] | None:
        return self._ultimos.get((sensor.medicion, sensor.nodo))

    async def historial(self, sensor: SensorConfig, variable: str, rango: str) -> list[tuple[datetime, float]]:
        seconds, window = RANGOS[rango]
        fn = "MAX" if sensor.variables[variable].agregacion == "max" else "AVG"
        desde_ms = int(time.time() * 1000) - seconds * 1000
        # variable sale del catálogo (validada en Servicio), nunca del usuario.
        query = (
            f"SELECT (ts_ms / ?) * ? AS t, {fn}(json_extract(msg, ?)) AS v FROM registros "
            "WHERE tipo = ? AND nodo = ? AND ts_ms >= ? AND json_extract(msg, ?) IS NOT NULL "
            "GROUP BY t ORDER BY t"
        )
        ruta = f"$.{variable}"
        params = (window * 1000, window * 1000, ruta, sensor.medicion, sensor.nodo, desde_ms, ruta)
        filas = await asyncio.to_thread(lambda: self._db.execute(query, params).fetchall())
        return [(datetime.fromtimestamp(t / 1000, timezone.utc), float(v)) for t, v in filas]

    async def disponible(self) -> bool:
        return self._ok
