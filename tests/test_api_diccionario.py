# tests/test_api_diccionario.py
import io

from fastapi.testclient import TestClient
from PIL import Image, UnidentifiedImageError

import backend.api.diccionario as diccionario_api
from backend.db.session import get_db
from backend.main import app


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None, lastrowid=None):
        self.executed = []
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.lastrowid = lastrowid

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetchone_results.pop(0) if self._fetchone_results else None

    def fetchall(self):
        return self._fetchall_results.pop(0) if self._fetchall_results else []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass


def _override_db(cursor):
    def _get_db():
        yield FakeConnection(cursor)
    return _get_db


def test_list_diccionario_endpoint():
    row = {"id": 1, "concepto": "taller", "alias": "[]", "tipo": "picto",
           "picto_id": 39586, "foto_path": None, "opciones": None, "creado": None}
    cursor = FakeCursor(fetchall_results=[[row]])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).get("/api/diccionario")

    assert resp.status_code == 200
    assert resp.json()[0]["concepto"] == "taller"
    app.dependency_overrides.clear()


def test_create_diccionario_endpoint_conflict_on_duplicate_concepto():
    cursor = FakeCursor(fetchone_results=[{"id": 1, "concepto": "taller"}])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).post("/api/diccionario", json={"concepto": "taller", "tipo": "picto", "picto_id": 1})

    assert resp.status_code == 409
    app.dependency_overrides.clear()


def test_create_diccionario_endpoint_happy_path():
    cursor = FakeCursor(fetchone_results=[
        None,  # find_diccionario_by_concepto_exacto: no existe
        {"id": 5, "concepto": "taller", "alias": "[]", "tipo": "picto",
         "picto_id": 39586, "foto_path": None, "opciones": None, "creado": None},
    ], lastrowid=5)
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).post("/api/diccionario", json={"concepto": "taller", "tipo": "picto", "picto_id": 39586})

    assert resp.status_code == 201
    assert resp.json()["id"] == 5
    app.dependency_overrides.clear()


def test_patch_diccionario_endpoint_404_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).patch("/api/diccionario/999", json={"concepto": "x"})

    assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_delete_diccionario_endpoint_happy_path():
    entrada = {"id": 3, "concepto": "x", "alias": "[]", "tipo": "picto",
               "picto_id": 1, "foto_path": None, "opciones": None, "creado": None}
    cursor = FakeCursor(fetchone_results=[entrada])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).delete("/api/diccionario/3")

    assert resp.status_code == 204
    app.dependency_overrides.clear()


def test_subir_foto_diccionario_endpoint_returns_400_on_unidentified_image(monkeypatch):
    entrada = {"id": 4, "concepto": "Marta", "alias": "[]", "tipo": "picto",
               "picto_id": None, "foto_path": None, "opciones": None, "creado": None}
    cursor = FakeCursor(fetchone_results=[entrada])
    app.dependency_overrides[get_db] = _override_db(cursor)

    def _raise_unidentified(*a, **k):
        raise UnidentifiedImageError("no se pudo decodificar")

    monkeypatch.setattr(diccionario_api, "guardar_foto", _raise_unidentified)

    resp = TestClient(app).post(
        "/api/diccionario/4/foto",
        files={"foto": ("foto.jpg", io.BytesIO(b"no es una imagen"), "image/jpeg")},
    )

    assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_subir_foto_diccionario_endpoint(monkeypatch, tmp_path):
    entrada = {"id": 4, "concepto": "Marta", "alias": "[]", "tipo": "foto",
               "picto_id": None, "foto_path": "fotos/nueva.jpg", "opciones": None, "creado": None}
    cursor = FakeCursor(fetchone_results=[
        {"id": 4, "concepto": "Marta", "alias": "[]", "tipo": "picto",
         "picto_id": None, "foto_path": None, "opciones": None, "creado": None},  # get antes de guardar
        entrada,  # get después de guardar
    ])
    app.dependency_overrides[get_db] = _override_db(cursor)
    monkeypatch.setattr(diccionario_api, "guardar_foto", lambda *a, **k: "fotos/nueva.jpg")

    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")
    buf.seek(0)

    resp = TestClient(app).post(
        "/api/diccionario/4/foto",
        files={"foto": ("foto.jpg", buf, "image/jpeg")},
    )

    assert resp.status_code == 200
    assert resp.json()["foto_path"] == "fotos/nueva.jpg"
    app.dependency_overrides.clear()
