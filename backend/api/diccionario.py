# backend/api/diccionario.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.clients import settings
from backend.db.queries.diccionario import (
    create_diccionario_entry,
    delete_diccionario_entry,
    find_diccionario_by_concepto_exacto,
    get_diccionario_entry,
    list_diccionario,
    update_diccionario_entry,
)
from backend.db.session import get_db
from backend.schemas.api import DiccionarioIn, DiccionarioOut, DiccionarioPatch
from backend.services.fotos import guardar_foto
from lib.log import get_logger

router = APIRouter(prefix="/api/diccionario", tags=["diccionario"])
logger = get_logger("pictohistorias")


@router.get("", response_model=list[DiccionarioOut])
def list_diccionario_endpoint(conn=Depends(get_db)):
    return list_diccionario(conn)


@router.post("", response_model=DiccionarioOut, status_code=201)
def create_diccionario_endpoint(body: DiccionarioIn, conn=Depends(get_db)):
    existente = find_diccionario_by_concepto_exacto(conn, body.concepto)
    if existente is not None:
        raise HTTPException(status_code=409, detail=f"Ya existe una entrada para «{body.concepto}»")
    nuevo_id = create_diccionario_entry(
        conn, concepto=body.concepto, tipo=body.tipo, alias=body.alias,
        picto_id=body.picto_id, foto_path=None, opciones=body.opciones,
    )
    return get_diccionario_entry(conn, nuevo_id)


@router.patch("/{entry_id}", response_model=DiccionarioOut)
def patch_diccionario_endpoint(entry_id: int, body: DiccionarioPatch, conn=Depends(get_db)):
    entrada = get_diccionario_entry(conn, entry_id)
    if entrada is None:
        raise HTTPException(status_code=404, detail=f"Entrada {entry_id} no encontrada")
    update_diccionario_entry(conn, entry_id, body.model_dump(exclude_none=True))
    return get_diccionario_entry(conn, entry_id)


@router.delete("/{entry_id}", status_code=204)
def delete_diccionario_endpoint(entry_id: int, conn=Depends(get_db)):
    entrada = get_diccionario_entry(conn, entry_id)
    if entrada is None:
        raise HTTPException(status_code=404, detail=f"Entrada {entry_id} no encontrada")
    delete_diccionario_entry(conn, entry_id)
    return Response(status_code=204)


@router.post("/{entry_id}/foto", response_model=DiccionarioOut)
async def subir_foto_diccionario_endpoint(entry_id: int, foto: UploadFile = File(...), conn=Depends(get_db)):
    entrada = get_diccionario_entry(conn, entry_id)
    if entrada is None:
        raise HTTPException(status_code=404, detail=f"Entrada {entry_id} no encontrada")
    try:
        contenido = await foto.read()
        foto_path = guardar_foto(contenido, foto.content_type, fotos_dir=settings.fotos_dir)
    except (ValueError, OSError) as exc:
        logger.error("Fallo subiendo foto para diccionario {}: {}", entry_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    update_diccionario_entry(conn, entry_id, {"tipo": "foto", "foto_path": foto_path, "picto_id": None})
    return get_diccionario_entry(conn, entry_id)
