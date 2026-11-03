from fastapi import APIRouter, HTTPException, Request

from ..influx import InfluxUnavailable

router = APIRouter()


@router.get("/salud")
async def salud(request: Request):
    try:
        response = await request.app.state.servicio.salud()
    except InfluxUnavailable as exc:
        raise HTTPException(status_code=503, detail={"influx": "no_disponible"}) from exc
    if response.influx == "no_disponible" and request.app.state.servicio.origen == "real":
        raise HTTPException(status_code=503, detail={"influx": "no_disponible"})
    return response
