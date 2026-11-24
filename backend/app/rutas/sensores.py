from fastapi import APIRouter, HTTPException, Query, Request

from ..errores import FuenteNoDisponible

router = APIRouter()


@router.get("/sensores")
async def sensores(request: Request):
    servicio = request.app.state.servicio
    return {"aula": servicio.registro.aula, "fuente": servicio.fuente, "sensores": servicio.catalogo()}


@router.get("/sensores/{sensor_id}/historial")
async def historial(
    sensor_id: str,
    request: Request,
    variable: str,
    rango: str = Query("1h", pattern="^(15m|1h|6h|24h|7d)$"),
):
    try:
        return await request.app.state.servicio.historial(sensor_id, variable, rango)
    except FuenteNoDisponible as exc:
        raise HTTPException(status_code=503, detail={"influx": "no_disponible"}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"{exc.args[0]} no encontrado") from exc
