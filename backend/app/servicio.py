import asyncio
from datetime import datetime, timezone
from typing import Any

from .estados import REGLAS
from .influx import InfluxRepository
from .modelos import (
    Diagnostico,
    HistorialRespuesta,
    LecturaSensor,
    PuntoHistorial,
    SaludRespuesta,
    SensorCatalogo,
    UltimasRespuesta,
    VariableLectura,
)
from .registro import RegistroConfig, SensorConfig
from .simulador import Simulador


class Servicio:
    def __init__(self, registro: RegistroConfig, repository: InfluxRepository | Simulador, origen: str):
        self.registro = registro
        self.repository = repository
        self.origen = origen

    def catalogo(self) -> list[SensorCatalogo]:
        return [SensorCatalogo.model_validate(sensor.model_dump(by_alias=True)) for sensor in self.registro.sensores]

    async def lectura(self, sensor: SensorConfig) -> LecturaSensor:
        record = await self.repository.ultima_lectura(sensor)
        now = datetime.now(timezone.utc)
        if record is None:
            return self._sin_datos(sensor)
        timestamp = record["time"]
        age = max(0.0, (now - timestamp).total_seconds())
        fields = record["fields"]
        estado_fn = REGLAS.get(sensor.estado.regla)
        if estado_fn is None:
            raise ValueError(f"Regla de estado desconocida: {sensor.estado.regla}")
        estado = estado_fn(fields, age, sensor.caduca_s)
        principal = fields.get(sensor.variable_principal)
        if principal in (-1, -2):
            principal = None
        variables = {}
        for name, config in sensor.variables.items():
            value = fields.get(name)
            if value in config.invalidos:
                value = None
            variables[name] = VariableLectura(valor=value, unidad=config.unidad, etiqueta=config.etiqueta)
        anomalies = str(fields.get("anomalias", "NINGUNA"))
        return LecturaSensor(
            id=sensor.id,
            nodo=sensor.nodo,
            tipo=sensor.medicion,
            etiqueta=sensor.etiqueta,
            valor=principal if isinstance(principal, (int, float)) else None,
            unidad=sensor.variables[sensor.variable_principal].unidad,
            estado=estado,
            actualizado=timestamp,
            edad_s=round(age, 2),
            variables=variables,
            anomalias=[] if anomalies == "NINGUNA" else [item for item in anomalies.split("|") if item],
            diagnostico=Diagnostico(seq=fields.get("seq"), perdidos=fields.get("perdidos")),
        )

    def _sin_datos(self, sensor: SensorConfig) -> LecturaSensor:
        principal = sensor.variables[sensor.variable_principal]
        return LecturaSensor(
            id=sensor.id,
            nodo=sensor.nodo,
            tipo=sensor.medicion,
            etiqueta=sensor.etiqueta,
            unidad=principal.unidad,
            estado="sin_datos",
            variables={
                name: VariableLectura(valor=None, unidad=config.unidad, etiqueta=config.etiqueta)
                for name, config in sensor.variables.items()
            },
        )

    async def ultimas(self) -> UltimasRespuesta:
        readings = await asyncio.gather(*(self.lectura(sensor) for sensor in self.registro.sensores))
        return UltimasRespuesta(
            aula=self.registro.aula,
            generado=datetime.now(timezone.utc),
            origen=self.origen,
            sensores=readings,
        )

    async def historial(self, sensor_id: str, variable: str, rango: str) -> HistorialRespuesta:
        sensor = self.registro.por_id(sensor_id)
        if sensor is None:
            raise KeyError("sensor")
        if variable not in sensor.variables:
            raise KeyError("variable")
        points = await self.repository.historial(sensor, variable, rango)
        window = {"15m": 10, "1h": 30, "6h": 120, "24h": 300, "7d": 1800}[rango]
        return HistorialRespuesta(
            id=sensor.id,
            variable=variable,
            unidad=sensor.variables[variable].unidad,
            rango=rango,
            ventana_s=window,
            puntos=[PuntoHistorial(t=time, v=value) for time, value in points],
        )

    async def salud(self) -> SaludRespuesta:
        latest = await self.ultimas()
        count = sum(reading.estado != "sin_datos" for reading in latest.sensores)
        connection = "en_linea" if count == len(latest.sensores) else "parcial" if count else "sin_datos"
        influx_ok = await self.repository.disponible()
        return SaludRespuesta(
            influx="ok" if influx_ok else "no_disponible",
            conexion=connection,
            sensores_esperados=len(latest.sensores),
            sensores_con_datos=count,
        )

