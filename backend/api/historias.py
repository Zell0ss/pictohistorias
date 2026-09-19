# backend/api/historias.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.clients import anthropic_client, embed_fn, qdrant_client, settings
from backend.db.queries.historias import (
    create_historia_con_pasos,
    get_historia_con_pasos,
    list_historias,
    update_historia,
)
from backend.db.session import get_db
from backend.schemas.api import HistoriaIn, HistoriaListItem, HistoriaOut, HistoriaPatch
from backend.services.generacion import generate_historia
from backend.services.pictos_cache import ensure_picto_png_cached
from backend.services.resolucion import resolve_paso_imagen
from lib.log import get_logger

router = APIRouter(prefix="/api/historias", tags=["historias"])
logger = get_logger("pictohistorias")


def _conceptos_diccionario(conn) -> list[str]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT concepto FROM diccionario")
        return [row["concepto"] for row in cursor.fetchall()]


@router.get("", response_model=list[HistoriaListItem])
def list_historias_endpoint(conn=Depends(get_db)):
    return list_historias(conn)


@router.post("", response_model=HistoriaOut, status_code=201)
def create_historia_endpoint(body: HistoriaIn, request: Request, conn=Depends(get_db)):
    conceptos = _conceptos_diccionario(conn)
    escribe = getattr(request.state, "escribe", "mamá")
    creada_por = getattr(request.state, "creada_por", None)

    try:
        generada = generate_historia(body.prompt, conceptos, anthropic_client, escribe=escribe)
    except (ValueError, ValidationError) as exc:
        logger.error("Fallo generando historia: {}", exc)
        raise HTTPException(status_code=502, detail="No se pudo generar la historia") from exc

    pasos_resueltos = []
    for paso_generado in generada.pasos:
        resolucion = resolve_paso_imagen(
            conn, qdrant_client, settings.qdrant_collection, embed_fn,
            paso_generado.concepto, paso_generado.candidatos_concepto,
        )
        if resolucion["picto_id"] is not None:
            ensure_picto_png_cached(resolucion["picto_id"], settings.arasaac_static_base)
        for candidato in resolucion["candidatos"]:
            ensure_picto_png_cached(candidato["id"], settings.arasaac_static_base)

        pasos_resueltos.append({
            "frase": paso_generado.frase,
            "concepto": paso_generado.concepto,
            "candidatos_concepto": paso_generado.candidatos_concepto,
            "imagen_tipo": resolucion["imagen_tipo"],
            "picto_id": resolucion["picto_id"],
            "foto_path": resolucion["foto_path"],
            "candidatos": resolucion["candidatos"],
            "concepto_ganador": resolucion["concepto_ganador"],
            "score_ganador": resolucion["score_ganador"],
        })
        logger.info(
            "paso resuelto: concepto={} candidatos_concepto={} concepto_ganador={} score_ganador={} via={} picto_id={} candidatos={}",
            paso_generado.concepto, paso_generado.candidatos_concepto, resolucion["concepto_ganador"],
            resolucion["score_ganador"], resolucion["via"], resolucion["picto_id"], resolucion["candidatos"],
        )

    historia_id = create_historia_con_pasos(conn, generada.titulo, body.prompt, pasos_resueltos, creada_por)
    logger.info(
        "historia generada: id={} pasos={} conceptos={} creada_por={}",
        historia_id, len(pasos_resueltos), [p["concepto"] for p in pasos_resueltos], creada_por,
    )

    return get_historia_con_pasos(conn, historia_id)


@router.get("/{historia_id}", response_model=HistoriaOut)
def get_historia_endpoint(historia_id: int, conn=Depends(get_db)):
    historia = get_historia_con_pasos(conn, historia_id)
    if historia is None:
        raise HTTPException(status_code=404, detail=f"Historia {historia_id} no encontrada")
    return historia


@router.patch("/{historia_id}", response_model=HistoriaOut)
def patch_historia_endpoint(historia_id: int, body: HistoriaPatch, conn=Depends(get_db)):
    historia = get_historia_con_pasos(conn, historia_id)
    if historia is None:
        raise HTTPException(status_code=404, detail=f"Historia {historia_id} no encontrada")
    update_historia(conn, historia_id, body.model_dump(exclude_none=True))
    return get_historia_con_pasos(conn, historia_id)
