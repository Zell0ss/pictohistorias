# backend/api/pasos.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.clients import settings
from backend.db.queries.diccionario import (
    create_diccionario_entry,
    find_diccionario_by_concepto_exacto,
    get_diccionario_entry,
    update_diccionario_entry,
)
from backend.db.queries.historias import get_paso, update_paso
from backend.db.session import get_db
from backend.schemas.api import DiccionarioOut, FijarIn, PasoOut, PasoPatch
from backend.services.fotos import guardar_foto
from lib.log import get_logger

router = APIRouter(prefix="/api/pasos", tags=["pasos"])
logger = get_logger("pictohistorias")


@router.patch("/{paso_id}", response_model=PasoOut)
def patch_paso_endpoint(paso_id: int, body: PasoPatch, conn=Depends(get_db)):
    paso = get_paso(conn, paso_id)
    if paso is None:
        raise HTTPException(status_code=404, detail=f"Paso {paso_id} no encontrado")
    fields = body.model_dump(exclude_none=True)
    if "picto_id" in fields:
        fields["imagen_tipo"] = "picto"
        fields["foto_path"] = None
    elif "foto_path" in fields:
        fields["imagen_tipo"] = "foto"
        fields["picto_id"] = None
    update_paso(conn, paso_id, fields)
    return get_paso(conn, paso_id)


@router.post("/{paso_id}/foto", response_model=PasoOut)
async def subir_foto_paso_endpoint(paso_id: int, foto: UploadFile = File(...), conn=Depends(get_db)):
    paso = get_paso(conn, paso_id)
    if paso is None:
        raise HTTPException(status_code=404, detail=f"Paso {paso_id} no encontrado")
    try:
        contenido = await foto.read()
        foto_path = guardar_foto(contenido, foto.content_type, fotos_dir=settings.fotos_dir)
    except (ValueError, OSError) as exc:
        logger.error("Fallo subiendo foto para paso {}: {}", paso_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    update_paso(conn, paso_id, {"imagen_tipo": "foto", "foto_path": foto_path, "picto_id": None})
    return get_paso(conn, paso_id)


@router.post("/{paso_id}/fijar", response_model=DiccionarioOut, status_code=201)
def fijar_paso_endpoint(paso_id: int, body: FijarIn, conn=Depends(get_db)):
    paso = get_paso(conn, paso_id)
    if paso is None:
        raise HTTPException(status_code=404, detail=f"Paso {paso_id} no encontrado")

    campos = {
        "concepto": body.concepto,
        "alias": body.alias or [],
        "tipo": paso["imagen_tipo"],
        "picto_id": paso["picto_id"],
        "foto_path": paso["foto_path"],
    }
    existente = find_diccionario_by_concepto_exacto(conn, body.concepto)
    if existente is not None:
        update_diccionario_entry(conn, existente["id"], campos)
        entry_id = existente["id"]
    else:
        entry_id = create_diccionario_entry(conn, **campos)
    logger.info("paso {} fijado en diccionario: concepto={} entry_id={}", paso_id, body.concepto, entry_id)
    return get_diccionario_entry(conn, entry_id)
