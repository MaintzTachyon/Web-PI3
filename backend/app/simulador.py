import math
from datetime import datetime, timedelta, timezone
from typing import Any

from .influx import RANGOS
from .registro import SensorConfig


class Simulador:
    def __init__(self) -> None:
        self._inicio = datetime.now(timezone.utc)

    def _fields(self, sensor: SensorConfig, elapsed: float) -> dict[str, Any]:
        if sensor.medicion == "co2":
            value = round(650 + 45 * math.sin(elapsed / 25), 1)
            return {
                "co2_ppm": value,
                "delta_30s": round(5 * math.cos(elapsed / 25), 1),
                "temp_c": 24.0 + math.sin(elapsed / 60),
                "nivel": "NORMAL",
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        value = 48 + 4 * math.sin(elapsed / 8)
        return {
            "leq_db": value,
            "lmax_db": value + 8,
            "pico_db": value + 12,
            "base_db": value - 5,
            "freq_dom_hz": 440,
            "calibrando": 0,
            "anomalias": "NINGUNA",
            "anom_bits": 0,
            "seq": int(elapsed / sensor.periodo_s),
            "perdidos": 0,
        }

    async def ultima_lectura(self, sensor: SensorConfig) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {"fields": self._fields(sensor, (now - self._inicio).total_seconds()), "time": now}

    async def historial(self, sensor: SensorConfig, variable: str, rango: str) -> list[tuple[datetime, float]]:
        seconds, window = RANGOS[rango]
        now = datetime.now(timezone.utc)
        points = []
        for offset in range(seconds, -1, -window):
            time = now - timedelta(seconds=offset)
            value = self._fields(sensor, (time - self._inicio).total_seconds()).get(variable)
            if isinstance(value, (int, float)):
                points.append((time, float(value)))
        return points

    async def disponible(self) -> bool:
        return True
