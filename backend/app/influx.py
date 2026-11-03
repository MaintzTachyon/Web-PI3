import asyncio
from datetime import datetime, timezone
from typing import Any

from .config import Settings
from .registro import SensorConfig


RANGOS = {"15m": (900, 10), "1h": (3600, 30), "6h": (21600, 120), "24h": (86400, 300), "7d": (604800, 1800)}


TOLERANCIA_S = 1.0


class InfluxUnavailable(RuntimeError):
    pass


def combinar_ultimos(records: list[Any]) -> dict[str, Any] | None:
    """Une el last() de cada field en una lectura, sin pivot (guía, sección 8.1).

    Un field que llegó como null en el último paquete no se guarda, así que su
    last() es de un paquete anterior; esos fields obsoletos se descartan.
    """
    con_hora = [record for record in records if record.get_time()]
    if not con_hora:
        return None
    actualizado: datetime = max(record.get_time() for record in con_hora)
    fields = {
        str(record.get_field()): record.get_value()
        for record in con_hora
        if (actualizado - record.get_time()).total_seconds() <= TOLERANCIA_S
    }
    return {"fields": fields, "time": actualizado}


class InfluxRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if settings.influx_token_lectura:
            from influxdb_client import InfluxDBClient

            self._client = InfluxDBClient(
                url=settings.influx_url,
                token=settings.influx_token_lectura,
                org=settings.influx_org,
            )

    def _query(self, query: str) -> list[Any]:
        if self._client is None:
            raise InfluxUnavailable("INFLUX_TOKEN_LECTURA no está configurado")
        try:
            return list(self._client.query_api().query(query, org=self.settings.influx_org))
        except Exception as exc:
            raise InfluxUnavailable("InfluxDB no está disponible") from exc

    async def ultima_lectura(self, sensor: SensorConfig) -> dict[str, Any] | None:
        query = (
            f'from(bucket: "{self.settings.influx_bucket}") |> range(start: -1h) '
            f'|> filter(fn: (r) => r._measurement == "{sensor.medicion}" and '
            f'r.nodo == "{sensor.nodo}" and r.grupo == "{self.settings.grupo}") |> last()'
        )
        tables = await asyncio.to_thread(self._query, query)
        return combinar_ultimos([record for table in tables for record in table.records])

    async def historial(self, sensor: SensorConfig, variable: str, rango: str) -> list[tuple[datetime, float]]:
        seconds, window = RANGOS[rango]
        field = sensor.variables[variable]
        query = (
            f'from(bucket: "{self.settings.influx_bucket}") |> range(start: -{seconds}s) '
            f'|> filter(fn: (r) => r._measurement == "{sensor.medicion}" and r.nodo == "{sensor.nodo}" '
            f'and r.grupo == "{self.settings.grupo}" and r._field == "{variable}") '
            f'|> aggregateWindow(every: {window}s, fn: {field.agregacion}, createEmpty: false)'
        )
        tables = await asyncio.to_thread(self._query, query)
        return [(record.get_time(), float(record.get_value())) for table in tables for record in table.records]

    async def disponible(self) -> bool:
        if self._client is None:
            return False
        try:
            await asyncio.to_thread(self._query, f'import "influxdata/influxdb/schema"\nschema.measurements(bucket: "{self.settings.influx_bucket}")')
            return True
        except InfluxUnavailable:
            return False

