# tests/test_api_pasos.py
from fastapi.testclient import TestClient
from PIL import UnidentifiedImageError

import backend.api.pasos as pasos_api
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


def test_patch_paso_con_picto_id_limpia_foto_path():
    paso = {"id": 1, "orden": 1, "frase": "x", "concepto": "coche",
            "candidatos_concepto": "[]", "imagen_tipo": "picto", "picto_id": 5,
            "foto_path": None, "candidatos": "[]", "concepto_ganador": "coche", "score_ganador": 1.0}
    cursor = FakeCursor(fetchone_results=[paso, paso])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).patch("/api/pasos/1", json={"picto_id": 39586})

    assert resp.status_code == 200
    sql, params = cursor.executed[1]  # [0] es el primer get_paso (SELECT), [1] el UPDATE
    assert "imagen_tipo = %s" in sql
    assert "foto_path = %s" in sql
    app.dependency_overrides.clear()


def test_patch_paso_404_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).patch("/api/pasos/999", json={"frase": "x"})

    assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_subir_foto_paso_endpoint(monkeypatch):
    import io
    from PIL import Image

    paso = {"id": 2, "orden": 1, "frase": "x", "concepto": "Marta",
            "candidatos_concepto": "[]", "imagen_tipo": "foto", "picto_id": None,
            "foto_path": "fotos/nueva.jpg", "candidatos": "[]", "concepto_ganador": None, "score_ganador": None}
    cursor = FakeCursor(fetchone_results=[paso, paso])
    app.dependency_overrides[get_db] = _override_db(cursor)
    monkeypatch.setattr(pasos_api, "guardar_foto", lambda *a, **k: "fotos/nueva.jpg")

    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")
    buf.seek(0)

    resp = TestClient(app).post("/api/pasos/2/foto", files={"foto": ("f.jpg", buf, "image/jpeg")})

    assert resp.status_code == 200
    assert resp.json()["foto_path"] == "fotos/nueva.jpg"
    app.dependency_overrides.clear()


def test_subir_foto_paso_endpoint_returns_400_on_unidentified_image(monkeypatch):
    import io

    paso = {"id": 2, "orden": 1, "frase": "x", "concepto": "Marta",
            "candidatos_concepto": "[]", "imagen_tipo": "foto", "picto_id": None,
            "foto_path": None, "candidatos": "[]", "concepto_ganador": None, "score_ganador": None}
    cursor = FakeCursor(fetchone_results=[paso])
    app.dependency_overrides[get_db] = _override_db(cursor)

    def _raise_unidentified(*a, **k):
        raise UnidentifiedImageError("no se pudo decodificar")

    monkeypatch.setattr(pasos_api, "guardar_foto", _raise_unidentified)

    resp = TestClient(app).post(
        "/api/pasos/2/foto", files={"foto": ("f.jpg", io.BytesIO(b"no es una imagen"), "image/jpeg")}
    )

    assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_fijar_paso_crea_entrada_nueva_en_diccionario(monkeypatch):
    paso = {"id": 3, "orden": 1, "frase": "x", "concepto": "taller",
            "candidatos_concepto": "[]", "imagen_tipo": "picto", "picto_id": 39586,
            "foto_path": None, "candidatos": "[]", "concepto_ganador": "taller", "score_ganador": 0.7}
    entrada_creada = {"id": 10, "concepto": "taller", "alias": "[]", "tipo": "picto",
                       "picto_id": 39586, "foto_path": None, "opciones": None, "creado": None}
    cursor = FakeCursor(fetchone_results=[paso, None, entrada_creada], lastrowid=10)
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).post("/api/pasos/3/fijar", json={"concepto": "taller"})

    assert resp.status_code == 201
    assert resp.json()["concepto"] == "taller"
    app.dependency_overrides.clear()


def test_fijar_paso_actualiza_entrada_existente(monkeypatch):
    paso = {"id": 4, "orden": 1, "frase": "x", "concepto": "Marta",
            "candidatos_concepto": "[]", "imagen_tipo": "foto", "picto_id": None,
            "foto_path": "fotos/marta.jpg", "candidatos": "[]", "concepto_ganador": None, "score_ganador": None}
    existente = {"id": 6, "concepto": "Marta"}
    actualizada = {"id": 6, "concepto": "Marta", "alias": "[]", "tipo": "foto",
                   "picto_id": None, "foto_path": "fotos/marta.jpg", "opciones": None, "creado": None}
    cursor = FakeCursor(fetchone_results=[paso, existente, actualizada])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).post("/api/pasos/4/fijar", json={"concepto": "Marta"})

    assert resp.status_code == 201
    assert resp.json()["foto_path"] == "fotos/marta.jpg"
    app.dependency_overrides.clear()


def test_fijar_paso_404_when_paso_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(app).post("/api/pasos/999/fijar", json={"concepto": "x"})

    assert resp.status_code == 404
    app.dependency_overrides.clear()
