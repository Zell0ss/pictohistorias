# tests/test_api_pictos.py
from fastapi.testclient import TestClient

import backend.api.pictos as pictos_api
from backend.main import app


def test_buscar_pictos_happy_path(monkeypatch):
    class FakePoint:
        def __init__(self, id, keywords):
            self.payload = {"id": id, "keywords": [{"keyword": k} for k in keywords]}
            self.score = 0.9

    monkeypatch.setattr(pictos_api, "embed_fn", lambda texts: [[1.0, 0.0]])
    monkeypatch.setattr(
        pictos_api, "search_pictos",
        lambda client, collection, vector, top, exclude_flagged: [FakePoint(1, ["coche"])],
    )
    monkeypatch.setattr(pictos_api, "ensure_picto_png_cached", lambda *a, **k: True)

    client = TestClient(app)
    response = client.get("/api/pictos/buscar", params={"q": "coche"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == 1
    assert body[0]["keywords"] == ["coche"]
    assert body[0]["url"] == "/pictos/1_300.png"


def test_buscar_pictos_caches_each_result(monkeypatch):
    class FakePoint:
        def __init__(self, id, keywords):
            self.payload = {"id": id, "keywords": [{"keyword": k} for k in keywords]}
            self.score = 0.9

    monkeypatch.setattr(pictos_api, "embed_fn", lambda texts: [[1.0, 0.0]])
    monkeypatch.setattr(
        pictos_api, "search_pictos",
        lambda client, collection, vector, top, exclude_flagged: [
            FakePoint(1, ["coche"]), FakePoint(2, ["autobus"]),
        ],
    )
    ids_cacheados = []
    monkeypatch.setattr(
        pictos_api, "ensure_picto_png_cached",
        lambda picto_id, static_base: ids_cacheados.append(picto_id) or True,
    )

    client = TestClient(app)
    response = client.get("/api/pictos/buscar", params={"q": "coche"})

    assert response.status_code == 200
    assert ids_cacheados == [1, 2]


def test_buscar_pictos_caches_bestsearch_fallback_results(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("Qdrant caido")

    monkeypatch.setattr(pictos_api, "embed_fn", _raise)

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"_id": 2, "keywords": [{"keyword": "autobus"}]}]

    monkeypatch.setattr(pictos_api.httpx, "get", lambda url, timeout: FakeResponse())
    ids_cacheados = []
    monkeypatch.setattr(
        pictos_api, "ensure_picto_png_cached",
        lambda picto_id, static_base: ids_cacheados.append(picto_id) or True,
    )

    client = TestClient(app)
    response = client.get("/api/pictos/buscar", params={"q": "autobus"})

    assert response.status_code == 200
    assert ids_cacheados == [2]


def test_buscar_pictos_falls_back_to_bestsearch_on_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("Qdrant caido")

    monkeypatch.setattr(pictos_api, "embed_fn", _raise)

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"_id": 2, "keywords": [{"keyword": "autobus"}]}]

    monkeypatch.setattr(pictos_api.httpx, "get", lambda url, timeout: FakeResponse())
    monkeypatch.setattr(pictos_api, "ensure_picto_png_cached", lambda *a, **k: True)

    client = TestClient(app)
    response = client.get("/api/pictos/buscar", params={"q": "autobus"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == 2
