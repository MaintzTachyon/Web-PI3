from collections.abc import Mapping

from .modelos import Estado


def estado_nivel_nodo(fields: Mapping[str, object], edad_s: float, caduca_s: float) -> Estado:
    if edad_s > caduca_s:
        return "sin_datos"
    if fields.get("co2_ppm") in (-1, -2) or "FALLO_SENSOR" in str(fields.get("anom_bits", "")):
        return "falla"
    return {
        "NORMAL": "normal",
        "ALERTA": "alerta",
        "CRITICO": "critico",
        "CALENTANDO": "calentando",
        "SIN_DATO": "sin_datos",
    }.get(str(fields.get("nivel", "SIN_DATO")), "sin_datos")  # type: ignore[return-value]


def estado_anomalias_nodo(fields: Mapping[str, object], edad_s: float, caduca_s: float) -> Estado:
    if edad_s > caduca_s:
        return "sin_datos"
    if fields.get("calibrando") in (1, True, "1"):
        return "calibrando"
    anomalias = str(fields.get("anomalias", "NINGUNA"))
    if "FALLO_AUDIO" in anomalias:
        return "falla"
    if anomalias and anomalias != "NINGUNA":
        return "alerta"
    return "normal"


REGLAS = {
    "nivel_nodo": estado_nivel_nodo,
    "anomalias_nodo": estado_anomalias_nodo,
}

