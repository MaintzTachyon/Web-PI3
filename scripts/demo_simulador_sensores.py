"""
Demo simulador de sensores L418

Simula los datos de los 6 sensores activos del proyecto sin necesidad de
hardware real (ESP32). Genera valores coherentes y eventos críticos
espóradicos para probar la respuesta del backend y el frontend.

Sensores simulados:
  1. sensor-co2-01   — CO₂ (ppm)
  2. sensor-audio-01 — Ruido (dB)
  3. sensor-luz-01   — Luz (lux)
  4. sensor-termico-01 — Ocupación (personas)
  5. sensor-magnetico-01 — Puerta (abierta/cerrada)
  6. sensor-ambiente-01 — Ambiente (temperatura, humedad, presión)

Uso:
    python scripts/demo_simulador_sensores.py

El script imprime por consola una lectura cada 2 segundos para cada sensor.
Presiona Ctrl+C para detener.
"""

import math
import time
from datetime import datetime, timezone

# Configuración de sensores (id, nodo, medición, variable principal, unidad)
SENSORES = [
    {
        "id": "sensor-co2-01",
        "nodo": 1,
        "medicion": "co2",
        "variable": "co2_ppm",
        "unidad": "ppm",
        "base": 650,
        "amplitud": 45,
        "periodo": 25,
    },
    {
        "id": "sensor-audio-01",
        "nodo": 2,
        "medicion": "audio",
        "variable": "leq_db",
        "unidad": "dB",
        "base": 48,
        "amplitud": 4,
        "periodo": 8,
    },
    {
        "id": "sensor-luz-01",
        "nodo": 4,
        "medicion": "luz",
        "variable": "lux",
        "unidad": "lux",
        "base": 200,
        "amplitud": 300,
        "periodo": 20,
    },
    {
        "id": "sensor-termico-01",
        "nodo": 5,
        "medicion": "termico",
        "variable": "ocupacion_est",
        "unidad": "personas",
        "base": 20,
        "amplitud": 15,
        "periodo": 45,
    },
    {
        "id": "sensor-magnetico-01",
        "nodo": 6,
        "medicion": "magnetico",
        "variable": "puerta_abierta",
        "unidad": "estado",
        "periodo": 30,
    },
    {
        "id": "sensor-ambiente-01",
        "nodo": 7,
        "medicion": "ambiente",
        "variable": "temp_c",
        "unidad": "°C",
        "base": 22,
        "amplitud": 8,
        "periodo": 55,
    },
]

# Intervalos (en segundos transcurridos) para simular eventos críticos
EVENTOS_CRITICOS = {
    "sensor-co2-01": 30,      # cada 30s: fallo de sensor
    "sensor-audio-01": 40,    # cada 40s: fallo de audio
    "sensor-luz-01": 25,      # cada 25s: iluminación baja / alerta
    "sensor-termico-01": 50,  # cada 50s: calibrando o alerta
    "sensor-magnetico-01": 30,# cada 30s: fallo de sensor magnético
    "sensor-ambiente-01": 55, # cada 55s: variación extrema
}


def generar_lectura(sensor, elapsed):
    """Genera una lectura simulada para un sensor dado el tiempo transcurrido."""
    medicion = sensor["medicion"]
    ahora = datetime.now(timezone.utc)

    # ---------- CO2 ----------
    if medicion == "co2":
        valor = round(sensor["base"] + sensor["amplitud"] * math.sin(elapsed / sensor["periodo"]), 1)
        if int(elapsed) % EVENTOS_CRITICOS[sensor["id"]] == 0:
            return {
                "id": sensor["id"],
                "nodo": sensor["nodo"],
                "tipo": sensor["medicion"],
                "etiqueta": "CO₂",
                "valor": -1,
                "unidad": sensor["unidad"],
                "estado": "falla",
                "anomalias": "FALLO_SENSOR",
                "actualizado": ahora.isoformat(),
                "edad_s": 0,
                "variables": {
                    "co2_ppm": {"valor": -1, "unidad": "ppm", "etiqueta": "CO₂", "decimales": 1},
                    "delta_30s": {"valor": round(5 * math.cos(elapsed / sensor["periodo"]), 1), "unidad": "ppm", "etiqueta": "Cambio en 30 s", "decimales": 0},
                    "temp_c": {"valor": 24.0 + math.sin(elapsed / 60), "unidad": "°C", "etiqueta": "Temp. interna del sensor", "decimales": 0, "uso": "diagnostico"},
                },
                "anomalias_lista": ["FALLO_SENSOR"],
            }
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "CO₂",
            "valor": valor,
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "co2_ppm": {"valor": valor, "unidad": "ppm", "etiqueta": "CO₂", "decimales": 1},
                "delta_30s": {"valor": round(5 * math.cos(elapsed / sensor["periodo"]), 1), "unidad": "ppm", "etiqueta": "Cambio en 30 s", "decimales": 0},
                "temp_c": {"valor": 24.0 + math.sin(elapsed / 60), "unidad": "°C", "etiqueta": "Temp. interna del sensor", "decimales": 0, "uso": "diagnostico"},
            },
            "anomalias_lista": [],
        }

    # ---------- Audio ----------
    elif medicion == "audio":
        valor = round(sensor["base"] + sensor["amplitud"] * math.sin(elapsed / sensor["periodo"]), 1)
        if int(elapsed) % EVENTOS_CRITICOS[sensor["id"]] == 0:
            return {
                "id": sensor["id"],
                "nodo": sensor["nodo"],
                "tipo": sensor["medicion"],
                "etiqueta": "Ruido",
                "valor": valor,
                "unidad": sensor["unidad"],
                "estado": "alerta",
                "anomalias": "FALLO_AUDIO",
                "actualizado": ahora.isoformat(),
                "edad_s": 0,
                "variables": {
                    "leq_db": {"valor": valor, "unidad": "dB", "etiqueta": "Nivel equivalente", "decimales": 1},
                    "lmax_db": {"valor": round(valor + 8, 1), "unidad": "dB", "etiqueta": "Máximo", "decimales": 1},
                    "pico_db": {"valor": round(valor + 12, 1), "unidad": "dB", "etiqueta": "Pico", "decimales": 1},
                    "base_db": {"valor": round(valor - 5, 1), "unidad": "dB", "etiqueta": "Ruido de fondo", "decimales": 1},
                    "freq_dom_hz": {"valor": 440, "unidad": "Hz", "etiqueta": "Frecuencia dominante", "decimales": 0},
                    "calibrando": {"valor": 0, "unidad": "0/1", "etiqueta": "Calibrando", "decimales": 0},
                },
                "anomalias_lista": ["FALLO_AUDIO"],
            }
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "Ruido",
            "valor": valor,
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "leq_db": {"valor": valor, "unidad": "dB", "etiqueta": "Nivel equivalente", "decimales": 1},
                "lmax_db": {"valor": round(valor + 8, 1), "unidad": "dB", "etiqueta": "Máximo", "decimales": 1},
                "pico_db": {"valor": round(valor + 12, 1), "unidad": "dB", "etiqueta": "Pico", "decimales": 1},
                "base_db": {"valor": round(valor - 5, 1), "unidad": "dB", "etiqueta": "Ruido de fondo", "decimales": 1},
                "freq_dom_hz": {"valor": 440, "unidad": "Hz", "etiqueta": "Frecuencia dominante", "decimales": 0},
                "calibrando": {"valor": 0, "unidad": "0/1", "etiqueta": "Calibrando", "decimales": 0},
            },
            "anomalias_lista": [],
        }

    # ---------- Luz ----------
    elif medicion == "luz":
        valor = round(sensor["base"] + sensor["amplitud"] * math.sin(elapsed / sensor["periodo"]), 1)
        if int(elapsed) % EVENTOS_CRITICOS[sensor["id"]] == 0:
            return {
                "id": sensor["id"],
                "nodo": sensor["nodo"],
                "tipo": sensor["medicion"],
                "etiqueta": "Luminosidad",
                "valor": -10,
                "unidad": sensor["unidad"],
                "estado": "alerta",
                "anomalias": "ALERTA",
                "actualizado": ahora.isoformat(),
                "edad_s": 0,
                "variables": {
                    "lux": {"valor": -10, "unidad": "lux", "etiqueta": "Iluminancia en el techo", "decimales": 0},
                    "lux_min": {"valor": 0, "unidad": "lux", "etiqueta": "Mínimo", "decimales": 0},
                    "lux_max": {"valor": 100, "unidad": "lux", "etiqueta": "Máximo", "decimales": 0},
                    "lux_mesa_est": {"valor": 0, "unidad": "lux", "etiqueta": "Estimación en la mesa", "decimales": 0},
                    "luces_cambio": {"valor": 0, "unidad": "estado", "etiqueta": "Cambio de luces", "decimales": 0, "uso": "diagnostico"},
                },
                "anomalias_lista": ["ALERTA"],
            }
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "Luminosidad",
            "valor": max(0, valor),
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "lux": {"valor": max(0, valor), "unidad": "lux", "etiqueta": "Iluminancia en el techo", "decimales": 0},
                "lux_min": {"valor": max(0, round(valor - 50, 1)), "unidad": "lux", "etiqueta": "Mínimo", "decimales": 0},
                "lux_max": {"valor": max(100, round(valor + 100, 1)), "unidad": "lux", "etiqueta": "Máximo", "decimales": 0},
                "lux_mesa_est": {"valor": max(0, round(valor * 0.6, 1)), "unidad": "lux", "etiqueta": "Estimación en la mesa", "decimales": 0},
                "luces_cambio": {"valor": 0, "unidad": "estado", "etiqueta": "Cambio de luces", "decimales": 0, "uso": "diagnostico"},
            },
            "anomalias_lista": [],
        }

    # ---------- Térmico ----------
    elif medicion == "termico":
        valor = round(sensor["base"] + sensor["amplitud"] * math.sin(elapsed / sensor["periodo"]), 1)
        if int(elapsed) % EVENTOS_CRITICOS[sensor["id"]] == 0:
            return {
                "id": sensor["id"],
                "nodo": sensor["nodo"],
                "tipo": sensor["medicion"],
                "etiqueta": "Ocupación",
                "valor": max(0, valor),
                "unidad": sensor["unidad"],
                "estado": "calibrando",
                "anomalias": "NINGUNA",
                "actualizado": ahora.isoformat(),
                "edad_s": 0,
                "variables": {
                    "ocupacion_est": {"valor": max(0, valor), "unidad": "personas", "etiqueta": "Personas en el aula", "decimales": 0},
                    "personas_en_vista": {"valor": max(1, round(valor)), "unidad": "personas", "etiqueta": "Personas en vista", "decimales": 0},
                    "entradas": {"valor": max(0, round(2 + math.sin(elapsed / 20))), "unidad": "personas", "etiqueta": "Entradas", "decimales": 0},
                    "salidas": {"valor": max(0, round(2 - math.sin(elapsed / 20))), "unidad": "personas", "etiqueta": "Salidas", "decimales": 0},
                    "cruces_dudosos": {"valor": 0, "unidad": "personas", "etiqueta": "Cruces dudosos", "decimales": 0},
                    "t_fondo": {"valor": round(22 + 5 * math.sin(elapsed / 50), 1), "unidad": "°C", "etiqueta": "Temperatura de fondo", "decimales": 2},
                    "t_max": {"valor": round(28 + 4 * math.sin(elapsed / 30), 1), "unidad": "°C", "etiqueta": "Temperatura máxima", "decimales": 2},
                    "calibrando": {"valor": 1, "unidad": "0/1", "etiqueta": "Calibrando", "decimales": 0, "uso": "diagnostico"},
                },
                "anomalias_lista": [],
            }
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "Ocupación",
            "valor": max(0, valor),
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "ocupacion_est": {"valor": max(0, valor), "unidad": "personas", "etiqueta": "Personas en el aula", "decimales": 0},
                "personas_en_vista": {"valor": max(1, round(valor)), "unidad": "personas", "etiqueta": "Personas en vista", "decimales": 0},
                "entradas": {"valor": max(0, round(2 + math.sin(elapsed / 20))), "unidad": "personas", "etiqueta": "Entradas", "decimales": 0},
                "salidas": {"valor": max(0, round(2 - math.sin(elapsed / 20))), "unidad": "personas", "etiqueta": "Salidas", "decimales": 0},
                "cruces_dudosos": {"valor": 0, "unidad": "personas", "etiqueta": "Cruces dudosos", "decimales": 0},
                "t_fondo": {"valor": round(22 + 5 * math.sin(elapsed / 50), 1), "unidad": "°C", "etiqueta": "Temperatura de fondo", "decimales": 2},
                "t_max": {"valor": round(28 + 4 * math.sin(elapsed / 30), 1), "unidad": "°C", "etiqueta": "Temperatura máxima", "decimales": 2},
                "calibrando": {"valor": 0, "unidad": "0/1", "etiqueta": "Calibrando", "decimales": 0, "uso": "diagnostico"},
            },
            "anomalias_lista": [],
        }

    # ---------- Magnético (puerta) ----------
    elif medicion == "magnetico":
        abierta = 1 if math.sin(elapsed / sensor["periodo"]) > 0 else 0
        if int(elapsed) % EVENTOS_CRITICOS[sensor["id"]] == 0:
            return {
                "id": sensor["id"],
                "nodo": sensor["nodo"],
                "tipo": sensor["medicion"],
                "etiqueta": "Puerta",
                "valor": abierta,
                "unidad": sensor["unidad"],
                "estado": "alerta",
                "anomalias": "FALLO_SENSOR",
                "actualizado": ahora.isoformat(),
                "edad_s": 0,
                "variables": {
                    "puerta_abierta": {"valor": abierta, "unidad": "estado", "etiqueta": "Estado de la puerta", "decimales": 0},
                    "aperturas": {"valor": max(0, round(0.5 * (1 - math.cos(elapsed / 20)))), "unidad": "veces", "etiqueta": "Aperturas", "decimales": 0},
                    "seg_abierta": {"valor": max(0.1, round(5 * math.sin(elapsed / 45), 1)), "unidad": "s", "etiqueta": "Tiempo abierta", "decimales": 1},
                    "campo_raw": {"valor": max(1000, round(2000 + 500 * math.sin(elapsed / 25))), "unidad": "cuentas", "etiqueta": "Campo magnético", "decimales": 0},
                },
                "anomalias_lista": ["FALLO_SENSOR"],
            }
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "Puerta",
            "valor": abierta,
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "puerta_abierta": {"valor": abierta, "unidad": "estado", "etiqueta": "Estado de la puerta", "decimales": 0},
                "aperturas": {"valor": max(0, round(0.5 * (1 - math.cos(elapsed / 20)))), "unidad": "veces", "etiqueta": "Aperturas", "decimales": 0},
                "seg_abierta": {"valor": max(0.1, round(5 * math.sin(elapsed / 45), 1)), "unidad": "s", "etiqueta": "Tiempo abierta", "decimales": 1},
                "campo_raw": {"valor": max(1000, round(2000 + 500 * math.sin(elapsed / 25))), "unidad": "cuentas", "etiqueta": "Campo magnético", "decimales": 0},
            },
            "anomalias_lista": [],
        }

    # ---------- Ambiente ----------
    else:  # ambiente
        return {
            "id": sensor["id"],
            "nodo": sensor["nodo"],
            "tipo": sensor["medicion"],
            "etiqueta": "Ambiente",
            "valor": round(sensor["base"] + sensor["amplitud"] * math.sin(elapsed / sensor["periodo"]), 1),
            "unidad": sensor["unidad"],
            "estado": "normal",
            "anomalias": "NINGUNA",
            "actualizado": ahora.isoformat(),
            "edad_s": 0,
            "variables": {
                "temp_c": {"valor": round(22 + 8 * math.sin(elapsed / 55), 1), "unidad": "°C", "etiqueta": "Temperatura", "decimales": 2},
                "hum_pct": {"valor": max(30, min(70, round(50 + 10 * math.cos(elapsed / 40), 1))), "unidad": "%", "etiqueta": "Humedad relativa", "decimales": 1},
                "pres_hpa": {"valor": max(1000, round(1013 + 20 * math.sin(elapsed / 60), 1)), "unidad": "hPa", "etiqueta": "Presión atmosférica", "decimales": 2},
            },
            "anomalias_lista": [],
        }


def formatear_estado(estado):
    """Devuelve el estado con un emoji para consola."""
    iconos = {
        "normal": "✅",
        "alerta": "⚠️",
        "critico": "🔴",
        "falla": "❌",
        "sin_datos": "⚫",
        "calibrando": "🔄",
        "calentando": "🔥",
    }
    return f"{iconos.get(estado, '❓')} {estado}"


def main():
    print("=" * 70)
    print("  Demo simulador de sensores — Aula L418")
    print("  Simulando 6 sensores sin hardware real")
    print("=" * 70)
    print()
    print("Sensores activos:")
    for s in SENSORES:
        print(f"  - {s['id']} (nodo {s['nodo']}) — {s['medicion']} ({s['variable']})")
    print()
    print("Presiona Ctrl+C para detener.\n")

    inicio = time.time()

    try:
        while True:
            elapsed = time.time() - inicio
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

            print(f"[{timestamp}] Lecturas simuladas (t={elapsed:.0f}s):")
            print("-" * 70)

            for sensor in SENSORES:
                lectura = generar_lectura(sensor, elapsed)
                estado_icono = formatear_estado(lectura["estado"])
                valor_str = f"{lectura['valor']} {lectura['unidad']}" if isinstance(lectura["valor"], (int, float)) else str(lectura["valor"])

                print(
                    f"  {estado_icono:3} {lectura['id']:20} | "
                    f"{lectura['etiqueta']:12} | "
                    f"valor={valor_str:12} | "
                    f"estado={lectura['estado']:12}"
                )

                if lectura["anomalias_lista"]:
                    for anom in lectura["anomalias_lista"]:
                        print(f"      └─ Anomalía: {anom}")

            print()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\nDemo detenida por el usuario.")


if __name__ == "__main__":
    main()