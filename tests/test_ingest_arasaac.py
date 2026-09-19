import json

from qdrant_client.models import PointStruct

from scripts.ingest_arasaac import run_ingest, save_raw_snapshot

RAW_PICTOS = [
    {"_id": 1, "keywords": [{"keyword": "coche", "meaning": "vehículo"}], "categories": [], "tags": [], "desc": "", "schematic": False},
    {"_id": 2, "keywords": [{"keyword": "autobús", "meaning": "vehículo de transporte público"}], "categories": [], "tags": [], "desc": "", "schematic": False},
]


class FakeDbConn:
    def __init__(self):
        self.upserted = []


class FakeQdrantClient:
    def __init__(self):
        self.upserted_points = []


def fake_upsert_picto(conn, picto):
    conn.upserted.append(picto)


def fake_upsert_pictos(client, collection, points):
    client.upserted_points.extend(points)
    client.last_collection = collection


def fake_embed_fn(texts):
    return [[float(i), 0.0] for i in range(len(texts))]


def test_run_ingest_upserts_db_and_qdrant(monkeypatch):
    monkeypatch.setattr("scripts.ingest_arasaac.upsert_picto", fake_upsert_picto)
    monkeypatch.setattr("scripts.ingest_arasaac.upsert_pictos", fake_upsert_pictos)

    conn = FakeDbConn()
    qdrant = FakeQdrantClient()

    count = run_ingest(RAW_PICTOS, conn, qdrant, "arasaac_es", fake_embed_fn)

    assert count == 2
    assert [p["id"] for p in conn.upserted] == [1, 2]
    assert len(qdrant.upserted_points) == 2
    assert qdrant.last_collection == "arasaac_es"
    assert isinstance(qdrant.upserted_points[0], PointStruct)
    assert qdrant.upserted_points[0].payload["id"] == 1
    assert qdrant.upserted_points[0].payload["keywords"] == RAW_PICTOS[0]["keywords"]


def test_save_raw_snapshot_writes_json_with_timestamp(tmp_path):
    path = save_raw_snapshot(RAW_PICTOS, cache_dir=str(tmp_path))

    assert path.exists()
    content = json.loads(path.read_text())
    assert "fetched_at" in content
    assert content["pictograms"] == RAW_PICTOS
