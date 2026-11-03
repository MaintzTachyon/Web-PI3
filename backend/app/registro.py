from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from .modelos import SensorCatalogo, Ubicacion, VariableCatalogo


class EstadoConfig(BaseModel):
    regla: str
    campo: str
    calibrando: str | None = None


class SensorConfig(SensorCatalogo):
    periodo_s: float = Field(gt=0)
    caduca_s: float = Field(gt=0)
    estado: EstadoConfig


class RegistroConfig(BaseModel):
    aula: str
    grupo: str
    sensores: list[SensorConfig]

    @model_validator(mode="after")
    def validar_registro(self) -> "RegistroConfig":
        ids = [sensor.id for sensor in self.sensores]
        if len(ids) != len(set(ids)):
            raise ValueError("Los ids de sensores deben ser únicos")
        claves = [(sensor.medicion, sensor.nodo) for sensor in self.sensores]
        if len(claves) != len(set(claves)):
            raise ValueError("No puede repetirse nodo dentro de una medición")
        for sensor in self.sensores:
            if sensor.variable_principal not in sensor.variables:
                raise ValueError(f"{sensor.id}: variable_principal no está declarada")
            for variable, config in sensor.variables.items():
                if not config.unidad.strip():
                    raise ValueError(f"{sensor.id}/{variable}: unidad obligatoria")
        return self

    def por_id(self, sensor_id: str) -> SensorConfig | None:
        return next((sensor for sensor in self.sensores if sensor.id == sensor_id), None)


def cargar_registro(path: Path) -> RegistroConfig:
    with path.open(encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file) or {}
    return RegistroConfig.model_validate(data)

