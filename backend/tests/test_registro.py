from pathlib import Path

import pytest

from app.registro import cargar_registro


def test_carga_catalogo():
    registro = cargar_registro(Path(__file__).parents[1] / "config" / "sensores.yaml")
    assert registro.aula == "L419"
    assert {sensor.id for sensor in registro.sensores} == {"sensor-co2-01", "sensor-audio-01"}


def test_rechaza_ids_repetidos(tmp_path):
    path = tmp_path / "sensores.yaml"
    path.write_text(
        """
aula: L419
grupo: grupo1
sensores:
  - id: repetido
    nodo: 1
    medicion: co2
    etiqueta: CO2
    periodo_s: 5
    caduca_s: 30
    ubicacion: {x: null, y: null}
    variable_principal: co2
    estado: {regla: nivel_nodo, campo: nivel}
    variables: {co2: {etiqueta: CO2, unidad: ppm, agregacion: mean}}
  - id: repetido
    nodo: 2
    medicion: audio
    etiqueta: Audio
    periodo_s: 1
    caduca_s: 10
    ubicacion: {x: null, y: null}
    variable_principal: db
    estado: {regla: anomalias_nodo, campo: anomalias}
    variables: {db: {etiqueta: dB, unidad: dB, agregacion: mean}}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ids"):
        cargar_registro(path)

