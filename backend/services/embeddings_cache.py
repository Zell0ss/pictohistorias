from backend.db.queries.concepto_embedding import get_cached_embedding, set_cached_embedding
from lib.normalize import normalize_concepto


def get_or_embed_concepto(conn, concepto: str, embed_fn) -> list[float]:
    normalizado = normalize_concepto(concepto)
    cached = get_cached_embedding(conn, normalizado)
    if cached is not None:
        return cached
    vector = embed_fn([concepto])[0]
    set_cached_embedding(conn, normalizado, vector)
    return vector
