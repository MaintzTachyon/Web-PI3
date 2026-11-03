import math
from datetime import datetime, timezone
from typing import Any

from .registro import SensorConfig


class Simulador:
    def __init__(self) -> None:
        self._inicio = datetime.now(timezone.utc)

    async def ultima_lectura(self, sensor: SensorConfig) -> dict[str, Any]:
        elapsed = (datetime.now(timezone.utc) - self._inicio).total_seconds()
        if sensor.medicion == "co2":
            value = round(650 + 45 * math.sin(elapsed / 25), 1)
            fields = {
                "co2_ppm": value,
                "delta_30s": round(5 * math.cos(elapsed / 25), 1),
                "temp_c": 24.0 + math.sin(elapsed / 60),
                "nivel": "NORMAL",
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        else:
            value = 48 + 4 * math.sin(elapsed / 8)
            fields = {
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
        return {"fields": fields, "time": datetime.now(timezone.utc)}

    async def historial(self, sensor: SensorConfig, variable: str, rango: str) -> list[tuple[datetime, float]]:
        now = datetime.now(timezone.utc)
        value = (await self.ultima_lectura(sensor))["fields"].get(variable)
        if not isinstance(value, (int, float)):
            return []
        return [(now, float(value))]

    async def disponible(self) -> bool:
        return True

