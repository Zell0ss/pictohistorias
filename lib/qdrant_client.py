from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams


def get_client(url: str) -> QdrantClient:
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient, name: str, vector_size: int = 1536) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        return

    actual = client.get_collection(name).config.params.vectors.size
    if actual != vector_size:
        raise ValueError(
            f"Collection '{name}' exists with vector size {actual} but {vector_size} was requested — "
            "embedder changed? Reindex required."
        )


def upsert_pictos(client: QdrantClient, collection: str, points: list[PointStruct], batch_size: int = 200) -> None:
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection, points=batch)


def _content_flags_filter() -> Filter:
    return Filter(
        must_not=[
            FieldCondition(key="schematic", match=MatchValue(value=True)),
            FieldCondition(key="sex", match=MatchValue(value=True)),
            FieldCondition(key="violence", match=MatchValue(value=True)),
        ]
    )


def search_pictos(
    client: QdrantClient,
    collection: str,
    vector: list[float],
    top: int = 5,
    exclude_flagged: bool = False,
):
    query_filter = _content_flags_filter() if exclude_flagged else None
    result = client.query_points(
        collection_name=collection, query=vector, limit=top, query_filter=query_filter
    )
    return result.points
