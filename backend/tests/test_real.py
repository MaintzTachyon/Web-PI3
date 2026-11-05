"""Modo real sin InfluxDB: se imita lo que Telegraf guarda a partir del JSON del gateway."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.config import SENSORES_PATH, Settings
from app.influx import InfluxRepository
from app.registro import cargar_registro
from app.servicio import Servicio
from app.sondeo import Sondeo

# Mensajes tal como los publica gateway.ino en utec/gemelo/grupo1/nodo<N>/<tipo>.
CO2 = {"nodo": 1, "mac": "AA:BB:CC:DD:EE:01", "seq": 120, "ts": None, "uptime_ms": 600000, "perdidos": 2,
       "tipo": "co2", "co2_ppm": 1120, "delta_30s": 35, "temp_c": None, "calentando": 0, "nivel": "ALERTA",
       "anomalias": "CO2_ALERTA_VENTILACION", "anom_bits": 4}
AUDIO = {"nodo": 2, "mac": "AA:BB:CC:DD:EE:02", "seq": 900, "ts": None, "uptime_ms": 900000, "perdidos": 0,
         "tipo": "audio", "leq_db": 62.4, "lmax_db": 71.0, "pico_db": 80.2, "base_db": 41.5, "freq_dom_hz": 512,
         "tonal": 0.21, "bloques_fuertes": 3, "calibrando": 0, "anomalias": "RUIDO_IMPACTO", "anom_bits": 2}


class Record:
    def __init__(self, field, value, time):
        self.field, self.value, self.time = field, value, time

    def get_field(self):
        return self.field

    def get_value(self):
        return self.value

    def get_time(self):
        return self.time


class Table:
    def __init__(self, records):
        self.records = records


def telegraf(mensaje: dict, time: datetime) -> list[Table]:
    """Como el parser json de telegraf.conf: tags fuera, null descartado, números a float."""
    tags = {"nodo", "mac", "tipo", "ts"}
    tables = []
    for field, value in mensaje.items():
        if field in tags or value is None:
            continue
        if isinstance(value, str) and field not in {"nivel", "anomalias"}:
            continue
        tables.append(Table([Record(field, float(value) if not isinstance(value, str) else value, time)]))
    return tables


class InfluxFalso(InfluxRepository):
    def __init__(self, datos: dict[str, list[Table]]):
        super().__init__(Settings(BACKEND_MODO="real"))
        self.datos = datos
        self.consultas: list[str] = []

    def _query(self, query: str):
        self.consultas.append(query)
        for medicion, tables in self.datos.items():
            if f'r._measurement == "{medicion}"' in query:
                return tables
        return []


def servicio(datos) -> tuple[Servicio, InfluxFalso]:
    repo = InfluxFalso(datos)
    return Servicio(cargar_registro(SENSORES_PATH), repo, "real"), repo


def test_lee_los_dos_sensores_desde_influx():
    ahora = datetime.now(timezone.utc)
    srv, repo = servicio({"co2": telegraf(CO2, ahora), "audio": telegraf(AUDIO, ahora)})
    respuesta = asyncio.run(srv.ultimas())
    co2, audio = {lectura.id: lectura for lectura in respuesta.sensores}.values()

    assert respuesta.origen == "real"
    assert co2.valor == 1120 and co2.unidad == "ppm" and co2.estado == "alerta"
    assert co2.variables["delta_30s"].valor == 35
    assert co2.variables["temp_c"].valor is None
    assert co2.anomalias == ["CO2_ALERTA_VENTILACION"]
    assert co2.diagnostico.seq == 120 and co2.diagnostico.perdidos == 2

    assert audio.valor == 62.4 and audio.unidad == "dB" and audio.estado == "alerta"
    assert audio.variables["freq_dom_hz"].valor == 512
    assert audio.anomalias == ["RUIDO_IMPACTO"]

    assert any('r.nodo == "1" and r.grupo == "grupo1"' in q for q in repo.consultas)
    assert any('r.nodo == "2" and r.grupo == "grupo1"' in q for q in repo.consultas)
    json.dumps(respuesta.model_dump(mode="json"))


def test_descarta_fields_obsoletos():
    ahora = datetime.now(timezone.utc)
    tables = telegraf(CO2, ahora) + [Table([Record("temp_c", 31.0, ahora - timedelta(minutes=5))])]
    srv, _ = servicio({"co2": tables, "audio": []})
    co2 = asyncio.run(srv.ultimas()).sensores[0]
    assert co2.variables["temp_c"].valor is None
    assert co2.actualizado == ahora


def test_fallos_reales():
    ahora = datetime.now(timezone.utc)
    fallo_co2 = {**CO2, "co2_ppm": -1, "nivel": "NORMAL", "anomalias": "FALLO_SENSOR", "anom_bits": 1}
    fallo_audio = {**AUDIO, "anomalias": "FALLO_AUDIO", "anom_bits": 1}
    srv, _ = servicio({"co2": telegraf(fallo_co2, ahora), "audio": telegraf(fallo_audio, ahora)})
    co2, audio = asyncio.run(srv.ultimas()).sensores
    assert co2.estado == "falla" and co2.valor is None and co2.variables["co2_ppm"].valor is None
    assert audio.estado == "falla"


def test_sensor_apagado_queda_sin_datos():
    viejo = datetime.now(timezone.utc) - timedelta(minutes=2)
    srv, _ = servicio({"co2": telegraf(CO2, viejo), "audio": []})
    co2, audio = asyncio.run(srv.ultimas()).sensores
    assert co2.estado == "sin_datos" and audio.estado == "sin_datos"


def test_stream_emite_lecturas_y_conexion():
    ahora = datetime.now(timezone.utc)
    srv, _ = servicio({"co2": telegraf(CO2, ahora), "audio": []})
    sondeo = Sondeo(srv, Settings(SONDEO_S=1))

    async def primeros(n):
        stream = sondeo.suscribir()
        eventos = [await anext(stream) for _ in range(n)]
        await stream.aclose()
        return eventos

    eventos = asyncio.run(primeros(3))
    assert eventos[0].startswith("event: lectura") and '"sensor-co2-01"' in eventos[0]
    assert eventos[1].startswith("event: lectura") and '"sensor-audio-01"' in eventos[1]
    assert eventos[2].startswith("event: conexion") and '"parcial"' in eventos[2]
