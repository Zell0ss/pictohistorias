# backend/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.config import router as config_router
from backend.api.diccionario import router as diccionario_router
from backend.api.historias import router as historias_router
from backend.api.pasos import router as pasos_router
from backend.api.pictos import router as pictos_router
from backend.clients import settings
from backend.middleware.cf_access import CloudflareAccessMiddleware

Path("cache/pictos").mkdir(parents=True, exist_ok=True)
Path(settings.fotos_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="PictoHistorias API", version="0.1.0")
app.add_middleware(CloudflareAccessMiddleware)
app.include_router(historias_router)
app.include_router(pasos_router)
app.include_router(pictos_router)
app.include_router(diccionario_router)
app.include_router(config_router)
app.mount("/pictos", StaticFiles(directory="cache/pictos"), name="pictos")
app.mount("/fotos", StaticFiles(directory=settings.fotos_dir), name="fotos")
app.mount("/prueba", StaticFiles(directory="backend/static", html=True), name="prueba")
# Montaje final (catch-all): sirve frontend/index.html en local para desarrollo
# sin nginx. En producción, nginx sirve "/" directamente y este mount no se usa.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
