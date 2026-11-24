import math
from datetime import datetime, timedelta, timezone
from typing import Any

from .influx import RANGOS
from .registro import SensorConfig


class Simulador:
    def __init__(self) -> None:
        self._inicio = datetime.now(timezone.utc)

    def _fields(self, sensor: SensorConfig, elapsed: float) -> dict[str, Any]:
        medicion = sensor.medicion
        # ---------- CO2 ----------
        if medicion == "co2":
            value = round(650 + 45 * math.sin(elapsed / 25), 1)
            # Cada 30 segundos aproximadamente, simular fallo de sensor
            if int(elapsed) % 30 == 0:
                return {
                    "co2_ppm": -1,  # valor inválido → pasa a "falla" en el backend
                    "delta_30s": round(5 * math.cos(elapsed / 25), 1),
                    "temp_c": 24.0 + math.sin(elapsed / 60),
                    "nivel": "FALLO_SENSOR",
                    "anomalias": "FALLO_SENSOR",
                    "anom_bits": 1,  # CO2_BIT_FALLO_SENSOR
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
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
        # ---------- Audio ----------
        elif medicion == "audio":
            value = round(48 + 4 * math.sin(elapsed / 8), 1)
            # Cada 40 segundos, simular fallo de audio
            if int(elapsed) % 40 == 0:
                return {
                    "leq_db": value,
                    "lmax_db": round(value + 8, 1),
                    "pico_db": round(value + 12, 1),
                    "base_db": round(value - 5, 1),
                    "freq_dom_hz": 440,
                    "calibrando": 0,
                    "anomalias": "FALLO_AUDIO",
                    "anom_bits": 1,  # AUD_BIT_FALLO
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            return {
                "leq_db": value,
                "lmax_db": round(value + 8, 1),
                "pico_db": round(value + 12, 1),
                "base_db": round(value - 5, 1),
                "freq_dom_hz": 440,
                "calibrando": 0,
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        # ---------- Luz ----------
        elif medicion == "luz":
            value = round(200 + 300 * math.sin(elapsed / 20), 1)
            # Cada 25 segundos, simular lectura de luz fuera de rango
            if int(elapsed) % 25 == 0:
                return {
                    "lux": -10,  # valor inválido → backend lo trata
                    "lux_min": max(0, round(value - 50, 1)),
                    "lux_max": max(100, round(value + 100, 1)),
                    "lux_mesa_est": max(0, round(value * 0.6, 1)),
                    "luces_cambio": 0,
                    "anomalias": "ALERTA",
                    "anom_bits": 1,  # LUZ_BIT_ILUMINACION_BAJA
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            return {
                "lux": max(0, value),
                "lux_min": max(0, round(value - 50, 1)),
                "lux_max": max(100, round(value + 100, 1)),
                "lux_mesa_est": max(0, round(value * 0.6, 1)),
                "luces_cambio": 0,
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        # ---------- Térmico ----------
        elif medicion == "termico":
            value = round(20 + 15 * math.sin(elapsed / 45), 1)
            # Cada 50 segundos, simular ocupación extrema o calibrando
            if int(elapsed) % 50 == 0:
                # Simular que el nodo dice está calibrando
                return {
                    "ocupacion_est": max(0, value),
                    "personas_en_vista": max(1, round(value)),
                    "entradas": max(0, round(2 + math.sin(elapsed / 20))),
                    "salidas": max(0, round(2 - math.sin(elapsed / 20))),
                    "cruces_dudosos": 0,
                    "t_fondo": round(22 + 5 * math.sin(elapsed / 50), 1),
                    "t_max": round(28 + 4 * math.sin(elapsed / 30), 1),
                    "calibrando": 1,  # nodo indicando que está calibrando
                    "anomalias": "NINGUNA",
                    "anom_bits": 0,
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            # Opcionalmente cada 60s poner ocupación extrema
            if int(elapsed) % 60 == 0 and int(elapsed) % 50 != 0:
                return {
                    "ocupacion_est": round(value),  # podría ser > 100 simulando error
                    "personas_en_vista": max(1, round(value)),
                    "entradas": max(0, round(2 + math.sin(elapsed / 20))),
                    "salidas": max(0, round(2 - math.sin(elapsed / 20))),
                    "cruces_dudosos": 0,
                    "t_fondo": round(22 + 5 * math.sin(elapsed / 50), 1),
                    "t_max": round(28 + 4 * math.sin(elapsed / 30), 1),
                    "calibrando": 0,
                    "anomalias": "ALERTA",
                    "anom_bits": 2,  # TER_BIT_OBJETO_ESTATICO
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            return {
                "ocupacion_est": max(0, value),
                "personas_en_vista": max(1, round(value)),
                "entradas": max(0, round(2 + math.sin(elapsed / 20))),
                "salidas": max(0, round(2 - math.sin(elapsed / 20))),
                "cruces_dudosos": 0,
                "t_fondo": round(22 + 5 * math.sin(elapsed / 50), 1),
                "t_max": round(28 + 4 * math.sin(elapsed / 30), 1),
                "calibrando": 0,
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        # ---------- Magnético (puerta) ----------
        elif medicion == "magnetico":
            ab = 1 if math.sin(elapsed / 30) > 0 else 0
            # Cada 35 segundos, simular apertura inesperada de puerta
            if int(elapsed) % 35 == 0:
                return {
                    "puerta_abierta": 1,  # puerta abierta repentinamente
                    "aperturas": max(0, round(0.5 * (1 - math.cos(elapsed / 20)))),
                    "seg_abierta": max(0.1, round(5 * math.sin(elapsed / 45), 1)),
                    "campo_raw": max(1000, round(2000 + 500 * math.sin(elapsed / 25))),
                    "anomalias": "NINGUNA",
                    "anom_bits": 0,
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            # Opcionalmente cada 30s, simular fallo de sensor magnético
            if int(elapsed) % 30 == 0:
                return {
                    "puerta_abierta": ab,
                    "aperturas": max(0, round(0.5 * (1 - math.cos(elapsed / 20)))),
                    "seg_abierta": max(0.1, round(5 * math.sin(elapsed / 45), 1)),
                    "campo_raw": max(1000, round(2000 + 500 * math.sin(elapsed / 25))),
                    "anomalias": "FALLO_SENSOR",
                    "anom_bits": 1,  # MAG_BIT_FALLO
                    "seq": int(elapsed / sensor.periodo_s),
                    "perdidos": 0,
                }
            return {
                "puerta_abierta": ab,
                "aperturas": max(0, round(0.5 * (1 - math.cos(elapsed / 20)))),
                "seg_abierta": max(0.1, round(5 * math.sin(elapsed / 45), 1)),
                "campo_raw": max(1000, round(2000 + 500 * math.sin(elapsed / 25))),
                "anomalias": "NINGUNA",
                "anom_bits": 0,
                "seq": int(elapsed / sensor.periodo_s),
                "perdidos": 0,
            }
        # ---------- Ambiente ----------
        else:  # ambiente
            return {
                "temp_c": round(22 + 8 * math.sin(elapsed / 55), 1),
                "hum_pct": max(30, min(70, round(50 + 10 * math.cos(elapsed / 40), 1))),
                "pres_hpa": max(1000, round(1013 + 20 * math.sin(elapsed / 60), 1)),
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