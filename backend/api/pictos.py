# backend/api/pictos.py
import httpx
from fastapi import APIRouter, Query

from backend.clients import embed_fn, qdrant_client, settings
from backend.services.pictos_cache import ensure_picto_png_cached
from lib.qdrant_client import search_pictos
from lib.log import get_logger

router = APIRouter(prefix="/api/pictos", tags=["pictos"])
logger = get_logger("pictohistorias")


@router.get("/buscar")
def buscar_pictos(q: str = Query(...)):
    try:
        vector = embed_fn([q])[0]
        resultados = search_pictos(
            qdrant_client, settings.qdrant_collection, vector, top=10, exclude_flagged=True
        )
        items = [
            {
                "id": r.payload["id"],
                "keywords": [kw["keyword"] for kw in r.payload["keywords"]],
                "url": f"/pictos/{r.payload['id']}_300.png",
            }
            for r in resultados
        ]
    except Exception as exc:
        logger.warning("Qdrant/OpenAI fallo en buscar, cayendo a bestsearch ARASAAC: {}", exc)
        items = _bestsearch_fallback(q)

    for item in items:
        ensure_picto_png_cached(item["id"], settings.arasaac_static_base)
    return items


def _bestsearch_fallback(q: str) -> list[dict]:
    url = f"{settings.arasaac_api_base}/pictograms/es/bestsearch/{q}"
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    resultados = response.json()
    return [
        {
            "id": r["_id"],
            "keywords": [kw["keyword"] for kw in r.get("keywords", [])],
            "url": f"/pictos/{r['_id']}_300.png",
        }
        for r in resultados[:10]
    ]
