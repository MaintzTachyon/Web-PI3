from fastapi import APIRouter, HTTPException, Request

from ..errores import FuenteNoDisponible

router = APIRouter()


@router.get("/salud")
async def salud(request: Request):
    try:
        response = await request.app.state.servicio.salud()
    except FuenteNoDisponible as exc:
        raise HTTPException(status_code=503, detail={"influx": "no_disponible"}) from exc
    if response.influx == "no_disponible" and request.app.state.servicio.fuente != "demo":
        raise HTTPException(status_code=503, detail={"influx": "no_disponible"})
    return response
