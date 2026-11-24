from fastapi import APIRouter, Request

from ..errores import FuenteNoDisponible

router = APIRouter()


@router.get("/lecturas/ultimas")
async def ultimas(request: Request):
    try:
        return await request.app.state.servicio.ultimas()
    except FuenteNoDisponible as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail={"influx": "no_disponible"}) from exc
