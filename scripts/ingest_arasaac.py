import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client.models import PointStruct

from lib.arasaac_client import fetch_all_pictograms
from lib.config import Settings
from lib.db import get_connection, upsert_picto
from lib.embeddings import embed_texts
from lib.qdrant_client import ensure_collection, get_client, upsert_pictos
from lib.transform import build_embedding_text, normalize_picto
from lib.log import get_logger

logger = get_logger("pictohistorias")


def save_raw_snapshot(data: list[dict], cache_dir: str) -> Path:
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pictograms": data,
    }
    out_path = cache_path / "arasaac_all_es.json"
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False))
    return out_path


def run_ingest(pictograms: list[dict], db_conn, qdrant_client, collection: str, embed_fn) -> int:
    normalized = [normalize_picto(p) for p in pictograms]

    for picto in normalized:
        upsert_picto(db_conn, picto)

    texts = [build_embedding_text(p) for p in normalized]
    vectors = embed_fn(texts)

    points = [
        PointStruct(
            id=picto["id"],
            vector=vector,
            payload={
                "id": picto["id"],
                "keywords": picto["keywords"],
                "categories": picto["categories"],
                "tags": picto["tags"],
            },
        )
        for picto, vector in zip(normalized, vectors)
    ]
    upsert_pictos(qdrant_client, collection, points)

    return len(normalized)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta del catálogo ARASAAC en MariaDB + Qdrant")
    parser.add_argument("--limit", type=int, default=None, help="Limitar a los primeros N pictos (pruebas)")
    args = parser.parse_args()

    settings = Settings()

    logger.info("Descargando catálogo ARASAAC ({})", settings.arasaac_locale)
    pictograms = fetch_all_pictograms(settings.arasaac_locale, settings.arasaac_api_base)
    snapshot_path = save_raw_snapshot(pictograms, cache_dir="cache")
    logger.info("Snapshot guardado en {}", snapshot_path)

    if args.limit is not None:
        pictograms = pictograms[: args.limit]

    db_conn = get_connection(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    qdrant = get_client(settings.qdrant_url)
    ensure_collection(qdrant, settings.qdrant_collection, vector_size=1536)

    def embed_fn(texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, api_key=settings.openai_api_key)

    count = run_ingest(pictograms, db_conn, qdrant, settings.qdrant_collection, embed_fn)
    logger.info("Ingeridos {} pictogramas", count)
    print(f"Ingeridos {count} pictogramas")


if __name__ == "__main__":
    main()
