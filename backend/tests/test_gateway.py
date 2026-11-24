"""Modo gateway: un gateway falso que responde como firmware/gateway_ap."""
import asyncio
import json
import time

import httpx
import pytest

from app.config import SENSORES_PATH, Settings
from app.errores import FuenteNoDisponible
from app.gateway import GatewayRepository
from app.registro import cargar_registro
from app.servicio import Servicio
from app.sondeo import Sondeo


def mensajes(ts):
    """Un mensaje por nodo, con los campos que arma procesar() en gateway_ap.ino."""
    base = lambda i, nodo, tipo: {"id": i, "nodo": nodo, "mac": "AA:BB:CC:DD:EE:0%d" % nodo, "seq": 10 + i,
                                  "ts": ts, "gw_ms": 60000 + i, "uptime_ms": 50000 + i, "perdidos": 0, "tipo": tipo}
    return [
        {**base(1, 1, "co2"), "co2_ppm": 1120, "delta_30s": 35, "temp_c": None, "calentando": 0,
         "nivel": "ALERTA", "anomalias": "CO2_ALERTA_VENTILACION", "anom_bits": 4},
        {**base(2, 2, "audio"), "leq_db": 62.4, "lmax_db": 71.0, "pico_db": 80.2, "base_db": 41.5,
         "freq_dom_hz": 512, "tonal": 0.21, "bloques_fuertes": 3, "calibrando": 0,
         "anomalias": "RUIDO_IMPACTO", "anom_bits": 2},
        {**base(3, 4, "luz"), "lux": 320.5, "lux_min": 300.0, "lux_max": 340.0, "lux_mesa_est": 240.4,
         "luces_cambio": 0, "anomalias": "NINGUNA", "anom_bits": 0},
        {**base(4, 5, "termico"), "entradas": 1, "salidas": 0, "ocupacion_est": 12, "personas_en_vista": 2,
         "cruces_dudosos": 0, "t_fondo": 23.1, "t_max": 33.4, "calibrando": 0, "anomalias": "NINGUNA", "anom_bits": 0},
        {**base(5, 6, "magnetico"), "puerta_abierta": 1, "aperturas": 2, "seg_abierta": 8.5, "campo_raw": 2100,
         "anomalias": "NINGUNA", "anom_bits": 0},
        {**base(6, 7, "ambiente"), "temp_c": 24.37, "hum_pct": 58.2, "pres_hpa": 1012.4,
         "anomalias": "TEMP_FUERA_CONFORT", "anom_bits": 2},
    ]


class GatewayFalso:
    def __init__(self, hora_ok=True, ts=None, hace_s=1):
        self.hora_ok = hora_ok
        self.registros = mensajes(ts if ts is not None else int(time.time() * 1000) if hora_ok else None)
        self.hace_s = hace_s
        self.hora_recibida = None
        self.desde_pedidos = []
        self.caido = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.caido:
            raise httpx.ConnectError("sin red", request=request)
        ruta, q = request.url.path, request.url.params
        if ruta == "/api/estado":
            return httpx.Response(200, json={"gw_ms": 60100, "hora_ok": self.hora_ok,
                                             "id_ultimo": self.registros[-1]["id"] if self.registros else 0})
        if ruta == "/api/hora":
            self.hora_recibida = int(q["epoch_ms"])
            return httpx.Response(200, json={"ts": self.hora_recibida})
        if ruta == "/api/ultimos":
            return httpx.Response(200, json=[
                {"nodo": m["nodo"], "tipo": m["tipo"], "hace_s": self.hace_s, "anomalias": m["anomalias"], "msg": m}
                for m in self.registros])
        if ruta == "/api/datos":
            desde = int(q["desde"])
            self.desde_pedidos.append(desde)
            lineas = [json.dumps(m) for m in self.registros if m["id"] > desde][: int(q["max"])]
            return httpx.Response(200, text="".join(linea + "\n" for linea in lineas))
        return httpx.Response(404)


def repo(tmp_path, gw):
    return GatewayRepository(Settings(BACKEND_MODO="gateway"), tmp_path / "gemelo.sqlite", transport=httpx.MockTransport(gw))


def lecturas(repositorio):
    srv = Servicio(cargar_registro(SENSORES_PATH), repositorio, "real", fuente="gateway")

    async def correr():
        await srv.sincronizar()
        return {lectura.id: lectura for lectura in (await srv.ultimas()).sensores}

    return srv, asyncio.run(correr())


def test_lee_los_seis_nodos(tmp_path):
    _, leidas = lecturas(repo(tmp_path, GatewayFalso()))
    assert set(leidas) == {"sensor-co2-01", "sensor-audio-01", "sensor-luz-01",
                           "sensor-termico-01", "sensor-magnetico-01", "sensor-ambiente-01"}
    co2 = leidas["sensor-co2-01"]
    assert co2.valor == 1120 and co2.estado == "alerta" and co2.anomalias == ["CO2_ALERTA_VENTILACION"]
    assert co2.variables["temp_c"].valor is None and co2.diagnostico.seq == 11
    assert leidas["sensor-audio-01"].valor == 62.4 and leidas["sensor-audio-01"].estado == "alerta"
    assert leidas["sensor-termico-01"].valor == 12 and leidas["sensor-termico-01"].estado == "normal"
    assert leidas["sensor-magnetico-01"].valor == 1
    assert leidas["sensor-ambiente-01"].valor == 24.37 and leidas["sensor-ambiente-01"].estado == "alerta"
    assert leidas["sensor-luz-01"].variables["lux_mesa_est"].valor == 240.4
    assert all(1 <= lectura.edad_s < 3 for lectura in leidas.values())


def test_historial_y_reanudacion(tmp_path):
    gw = GatewayFalso()
    srv, _ = lecturas(repo(tmp_path, gw))
    historial = asyncio.run(srv.historial("sensor-co2-01", "co2_ppm", "15m"))
    assert [p.v for p in historial.puntos] == [1120.0]
    # Un backend nuevo sobre la misma base pide solo lo que no tiene.
    gw2 = GatewayFalso()
    lecturas(repo(tmp_path, gw2))
    assert gw2.desde_pedidos[0] == 6


def test_envia_la_hora_y_estima_ts_sin_hora(tmp_path):
    gw = GatewayFalso(hora_ok=False)
    srv, leidas = lecturas(repo(tmp_path, gw))
    assert abs(gw.hora_recibida - time.time() * 1000) < 5000
    assert leidas["sensor-co2-01"].valor == 1120
    historial = asyncio.run(srv.historial("sensor-audio-01", "leq_db", "15m"))
    assert len(historial.puntos) == 1


def test_dato_de_antes_del_reinicio_queda_sin_datos(tmp_path):
    hace_una_hora = int((time.time() - 3600) * 1000)
    _, leidas = lecturas(repo(tmp_path, GatewayFalso(ts=hace_una_hora, hace_s=-1)))
    assert leidas["sensor-co2-01"].estado == "sin_datos"


def test_gateway_caido(tmp_path):
    gw = GatewayFalso()
    gw.caido = True
    repositorio = repo(tmp_path, gw)
    with pytest.raises(FuenteNoDisponible):
        asyncio.run(repositorio.sincronizar())
    assert asyncio.run(repositorio.disponible()) is False


def test_stream_avisa_gateway_caido(tmp_path):
    gw = GatewayFalso()
    gw.caido = True
    srv = Servicio(cargar_registro(SENSORES_PATH), repo(tmp_path, gw), "real", fuente="gateway")
    sondeo = Sondeo(srv, Settings(SONDEO_S=1))

    async def ciclo():
        stream = sondeo.suscribir()
        primeros = [await anext(stream) for _ in range(7)]   # 6 lecturas + conexion inicial
        await sondeo.iniciar()
        siguiente = ""
        while not siguiente.startswith("event: conexion"):
            siguiente = await asyncio.wait_for(anext(stream), 5)
        await sondeo.detener()
        await stream.aclose()
        return primeros, siguiente

    primeros, siguiente = asyncio.run(ciclo())
    assert all('"sin_datos"' in e for e in primeros[:6])
    assert siguiente.startswith("event: conexion") and '"no_disponible"' in siguiente
