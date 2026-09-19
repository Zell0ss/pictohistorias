# backend/api/config.py
from fastapi import APIRouter

from backend.clients import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config():
    return {"nombre_nino": settings.nombre_nino.strip()}
