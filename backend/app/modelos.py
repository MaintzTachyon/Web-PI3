from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Estado = Literal["normal", "alerta", "critico", "calentando", "calibrando", "falla", "sin_datos"]
Conexion = Literal["en_linea", "parcial", "sin_datos"]


class Ubicacion(BaseModel):
    x: float | None = None
    y: float | None = None


class VariableCatalogo(BaseModel):
    etiqueta: str
    unidad: str
    decimales: int = 0
    agregacion: Literal["mean", "max"]
    uso: str | None = None
    invalidos: list[float | int] = []


class SensorCatalogo(BaseModel):
    id: str
    nodo: int
    tipo: str = Field(alias="medicion")
    etiqueta: str
    ubicacion: Ubicacion
    variable_principal: str
    variables: dict[str, VariableCatalogo]

    model_config = ConfigDict(populate_by_name=True)

    @property
    def medicion(self) -> str:
        return self.tipo


class VariableLectura(BaseModel):
    valor: float | int | str | None
    unidad: str
    etiqueta: str


class Diagnostico(BaseModel):
    seq: int | None = None
    perdidos: int | None = None


class LecturaSensor(BaseModel):
    id: str
    nodo: int
    tipo: str
    etiqueta: str
    valor: float | int | None = None
    unidad: str
    estado: Estado
    actualizado: datetime | None = None
    edad_s: float | None = None
    variables: dict[str, VariableLectura] = {}
    anomalias: list[str] = []
    diagnostico: Diagnostico = Diagnostico()


class UltimasRespuesta(BaseModel):
    aula: str
    generado: datetime
    origen: Literal["real", "demo"]
    sensores: list[LecturaSensor]


class PuntoHistorial(BaseModel):
    t: datetime
    v: float


class HistorialRespuesta(BaseModel):
    id: str
    variable: str
    unidad: str
    rango: str
    ventana_s: int
    puntos: list[PuntoHistorial]


class SaludRespuesta(BaseModel):
    backend: Literal["ok"] = "ok"
    influx: Literal["ok", "no_disponible"]
    conexion: Conexion
    sensores_esperados: int
    sensores_con_datos: int
