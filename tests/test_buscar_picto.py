from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from lib.qdrant_client import ensure_collection, upsert_pictos
from scripts.buscar_picto import search_picto


def test_search_picto_returns_ranked_results():
    client = QdrantClient(":memory:")
    ensure_collection(client, "arasaac_es", vector_size=4)
    points = [
        PointStruct(
            id=1,
            vector=[1.0, 0.0, 0.0, 0.0],
            payload={"id": 1, "keywords": [{"keyword": "coche"}, {"keyword": "automóvil"}]},
        ),
        PointStruct(
            id=2,
            vector=[0.0, 1.0, 0.0, 0.0],
            payload={"id": 2, "keywords": [{"keyword": "autobús"}]},
        ),
    ]
    upsert_pictos(client, "arasaac_es", points)

    def fake_embed_fn(texts):
        return [[1.0, 0.0, 0.0, 0.0]]

    results = search_picto("coche", client, "arasaac_es", fake_embed_fn, top=1)

    assert results == [{"id": 1, "keywords": ["coche", "automóvil"], "score": results[0]["score"]}]
    assert results[0]["score"] > 0.9
