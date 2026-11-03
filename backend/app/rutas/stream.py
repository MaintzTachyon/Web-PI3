from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/stream")
async def stream(request: Request):
    return StreamingResponse(
        request.app.state.sondeo.suscribir(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

