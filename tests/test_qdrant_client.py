from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from lib.qdrant_client import ensure_collection, search_pictos, upsert_pictos


def test_ensure_collection_creates_when_missing():
    client = QdrantClient(":memory:")

    ensure_collection(client, "test_col", vector_size=4)

    names = [c.name for c in client.get_collections().collections]
    assert "test_col" in names


def test_ensure_collection_is_idempotent():
    client = QdrantClient(":memory:")

    ensure_collection(client, "test_col", vector_size=4)
    ensure_collection(client, "test_col", vector_size=4)

    names = [c.name for c in client.get_collections().collections]
    assert names.count("test_col") == 1


def test_ensure_collection_raises_on_vector_size_mismatch():
    client = QdrantClient(":memory:")

    ensure_collection(client, "test_col", vector_size=4)

    try:
        ensure_collection(client, "test_col", vector_size=8)
        assert False, "expected ValueError for vector size mismatch"
    except ValueError as exc:
        assert "test_col" in str(exc)
        assert "4" in str(exc)
        assert "8" in str(exc)


def test_upsert_and_search_roundtrip():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_col", vector_size=4)
    points = [
        PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"id": 1, "keywords": ["coche"]}),
        PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"id": 2, "keywords": ["autobús"]}),
    ]

    upsert_pictos(client, "test_col", points)
    results = search_pictos(client, "test_col", vector=[1.0, 0.0, 0.0, 0.0], top=1)

    assert len(results) == 1
    assert results[0].payload["keywords"] == ["coche"]


def test_upsert_pictos_batches_large_lists():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_col", vector_size=4)

    # Create 5 points with distinct orthogonal vectors to upsert with batch_size=2
    # This should result in 3 batches: [2 points], [2 points], [1 point]
    points = [
        PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"id": 1, "name": "point_1"}),
        PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"id": 2, "name": "point_2"}),
        PointStruct(id=3, vector=[0.0, 0.0, 1.0, 0.0], payload={"id": 3, "name": "point_3"}),
        PointStruct(id=4, vector=[0.0, 0.0, 0.0, 1.0], payload={"id": 4, "name": "point_4"}),
        PointStruct(id=5, vector=[0.5, 0.5, 0.0, 0.0], payload={"id": 5, "name": "point_5"}),
    ]

    # Wrap client.upsert to count calls
    original_upsert = client.upsert
    call_count = 0

    def counting_upsert(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_upsert(*args, **kwargs)

    client.upsert = counting_upsert

    # Upsert with batch_size=2 (5 points should make 3 batches)
    upsert_pictos(client, "test_col", points, batch_size=2)

    # Verify batching happened
    assert call_count == 3, f"Expected 3 upsert calls for 5 points at batch_size=2, got {call_count}"

    # Verify all 5 points are retrievable by searching with their unique vectors
    search_vectors = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.5, 0.5, 0.0, 0.0],
    ]

    for i, search_vec in enumerate(search_vectors, start=1):
        results = search_pictos(client, "test_col", vector=search_vec, top=1)
        assert len(results) == 1, f"No results for point {i}"
        assert results[0].id == i, f"Expected id={i}, got id={results[0].id}"


def test_search_pictos_excludes_flagged_content_when_requested():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_col", vector_size=4)
    points = [
        PointStruct(
            id=1, vector=[1.0, 0.0, 0.0, 0.0],
            payload={"id": 1, "keywords": ["limpio"], "schematic": False, "sex": False, "violence": False},
        ),
        PointStruct(
            id=2, vector=[1.0, 0.0, 0.0, 0.0],
            payload={"id": 2, "keywords": ["esquematico"], "schematic": True, "sex": False, "violence": False},
        ),
    ]
    upsert_pictos(client, "test_col", points)

    resultados = search_pictos(client, "test_col", vector=[1.0, 0.0, 0.0, 0.0], top=5, exclude_flagged=True)

    ids = [r.id for r in resultados]
    assert 1 in ids
    assert 2 not in ids


def test_search_pictos_includes_flagged_content_by_default():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_col", vector_size=4)
    points = [
        PointStruct(
            id=2, vector=[1.0, 0.0, 0.0, 0.0],
            payload={"id": 2, "keywords": ["esquematico"], "schematic": True, "sex": False, "violence": False},
        ),
    ]
    upsert_pictos(client, "test_col", points)

    resultados = search_pictos(client, "test_col", vector=[1.0, 0.0, 0.0, 0.0], top=5)

    assert [r.id for r in resultados] == [2]
