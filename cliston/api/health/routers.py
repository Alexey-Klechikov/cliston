from api.health.models import HealthResponse
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
