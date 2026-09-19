# tests/test_api_historias.py
from fastapi.testclient import TestClient

import backend.api.historias as historias_api
from backend.db.session import get_db
from backend.main import app
from backend.schemas.generacion import HistoriaGenerada, PasoGenerado


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


def test_create_historia_happy_path(monkeypatch):
    cursor = FakeCursor(fetchall_results=[[]], lastrowid=10)
    app.dependency_overrides[get_db] = _override_db(cursor)

    paso = PasoGenerado(frase="Subo al coche", concepto="coche", candidatos_concepto=["vehiculo", "transporte"])
    generada = HistoriaGenerada(titulo="Al taller", pasos=[paso, paso, paso, paso])
    monkeypatch.setattr(historias_api, "generate_historia", lambda prompt, conceptos, client, **kwargs: generada)
    monkeypatch.setattr(
        historias_api, "resolve_paso_imagen",
        lambda conn, qc, coll, ef, concepto, candidatos: {
            "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
            "candidatos": [{"id": 5, "schematic": False}],
            "concepto_ganador": "coche", "score_ganador": 0.85, "via": "principal",
        },
    )
    monkeypatch.setattr(historias_api, "ensure_picto_png_cached", lambda *a, **k: True)

    historia_row = {
        "id": 10, "titulo": "Al taller", "prompt": "texto", "archivada": False,
        "creada": None, "actualizada": None,
    }
    cursor._fetchone_results = [historia_row]
    cursor._fetchall_results.append([
        {"id": 1, "orden": 1, "frase": "Subo al coche", "concepto": "coche",
         "candidatos_concepto": '["vehiculo", "transporte"]',
         "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
         "candidatos": '[{"id": 5, "schematic": false}]',
         "concepto_ganador": "coche", "score_ganador": 0.85}
    ])

    client = TestClient(app)
    response = client.post("/api/historias", json={"prompt": "texto"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 10
    assert body["pasos"][0]["picto_id"] == 5

    app.dependency_overrides.clear()


def test_create_historia_caches_candidate_pictos_not_just_winner(monkeypatch):
    cursor = FakeCursor(fetchall_results=[[]], lastrowid=10)
    app.dependency_overrides[get_db] = _override_db(cursor)

    paso = PasoGenerado(frase="Subo al coche", concepto="coche", candidatos_concepto=["vehiculo", "transporte"])
    generada = HistoriaGenerada(titulo="Al taller", pasos=[paso, paso, paso, paso])
    monkeypatch.setattr(historias_api, "generate_historia", lambda prompt, conceptos, client, **kwargs: generada)
    monkeypatch.setattr(
        historias_api, "resolve_paso_imagen",
        lambda conn, qc, coll, ef, concepto, candidatos: {
            "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
            "candidatos": [{"id": 5, "schematic": False}, {"id": 6, "schematic": False}, {"id": 7, "schematic": True}],
            "concepto_ganador": "coche", "score_ganador": 0.85, "via": "principal",
        },
    )
    ids_cacheados = []
    monkeypatch.setattr(
        historias_api, "ensure_picto_png_cached",
        lambda picto_id, static_base: ids_cacheados.append(picto_id) or True,
    )

    historia_row = {
        "id": 10, "titulo": "Al taller", "prompt": "texto", "archivada": False,
        "creada": None, "actualizada": None,
    }
    cursor._fetchone_results = [historia_row]
    cursor._fetchall_results.append([
        {"id": 1, "orden": 1, "frase": "Subo al coche", "concepto": "coche",
         "candidatos_concepto": '["vehiculo", "transporte"]',
         "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
         "candidatos": '[{"id": 5, "schematic": false}, {"id": 6, "schematic": false}, {"id": 7, "schematic": true}]',
         "concepto_ganador": "coche", "score_ganador": 0.85}
    ])

    client = TestClient(app)
    response = client.post("/api/historias", json={"prompt": "texto"})

    assert response.status_code == 201
    # Por cada uno de los 4 pasos: el picto ganador (5) y los dos candidatos adicionales (6, 7) deben cachearse.
    assert ids_cacheados == [5, 5, 6, 7] * 4

    app.dependency_overrides.clear()


def test_create_historia_returns_502_on_generation_failure(monkeypatch):
    cursor = FakeCursor(fetchall_results=[[]])
    app.dependency_overrides[get_db] = _override_db(cursor)

    def _raise(*args, **kwargs):
        raise ValueError("JSON invalido dos veces")

    monkeypatch.setattr(historias_api, "generate_historia", _raise)

    client = TestClient(app)
    response = client.post("/api/historias", json={"prompt": "texto"})

    assert response.status_code == 502
    app.dependency_overrides.clear()


def test_get_historia_404_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.get("/api/historias/999")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_list_historias_endpoint_returns_list():
    cursor = FakeCursor(fetchall_results=[[
        {"id": 1, "titulo": "Al taller", "creada": None, "actualizada": None},
        {"id": 2, "titulo": "Al parque", "creada": None, "actualizada": None},
    ]])
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.get("/api/historias")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[0]["titulo"] == "Al taller"

    app.dependency_overrides.clear()


def test_patch_historia_endpoint_happy_path():
    historia_row = {
        "id": 10, "titulo": "Al taller", "prompt": "texto", "archivada": False,
        "creada": None, "actualizada": None, "pasos": [],
    }
    historia_row_actualizada = {
        "id": 10, "titulo": "Al taller (editado)", "prompt": "texto", "archivada": False,
        "creada": None, "actualizada": None, "pasos": [],
    }
    cursor = FakeCursor(
        fetchone_results=[historia_row, historia_row_actualizada],
        fetchall_results=[[], []],
    )
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.patch("/api/historias/10", json={"titulo": "Al taller (editado)"})

    assert response.status_code == 200
    body = response.json()
    assert body["titulo"] == "Al taller (editado)"

    update_calls = [sql for sql, params in cursor.executed if sql.strip().startswith("UPDATE historia")]
    assert len(update_calls) == 1
    assert "titulo = %s" in update_calls[0]

    app.dependency_overrides.clear()


def test_patch_historia_endpoint_404_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.patch("/api/historias/999", json={"titulo": "no existe"})

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_patch_paso_endpoint_happy_path():
    paso_row = {
        "id": 1, "orden": 1, "frase": "Subo al coche", "concepto": "coche",
        "candidatos_concepto": '["vehiculo", "transporte"]',
        "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
        "candidatos": '[{"id": 5, "schematic": false}]',
        "concepto_ganador": "coche", "score_ganador": 0.85,
    }
    paso_row_actualizado = {
        "id": 1, "orden": 1, "frase": "Me subo al coche", "concepto": "coche",
        "candidatos_concepto": '["vehiculo", "transporte"]',
        "imagen_tipo": "picto", "picto_id": 5, "foto_path": None,
        "candidatos": '[{"id": 5, "schematic": false}]',
        "concepto_ganador": "coche", "score_ganador": 0.85,
    }
    cursor = FakeCursor(fetchone_results=[paso_row, paso_row_actualizado])
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.patch("/api/pasos/1", json={"frase": "Me subo al coche"})

    assert response.status_code == 200
    body = response.json()
    assert body["frase"] == "Me subo al coche"

    app.dependency_overrides.clear()


def test_patch_paso_endpoint_404_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    app.dependency_overrides[get_db] = _override_db(cursor)

    client = TestClient(app)
    response = client.patch("/api/pasos/999", json={"frase": "no existe"})

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_create_historia_endpoint_usa_escribe_de_request_state(monkeypatch):
    llamada = {}

    def fake_generate_historia(prompt, conceptos, client, escribe="mamá"):
        llamada["escribe"] = escribe
        class Generada:
            titulo = "Título"
            pasos = []
        return Generada()

    monkeypatch.setattr(historias_api, "generate_historia", fake_generate_historia)

    cursor = FakeCursor(fetchall_results=[[]], lastrowid=1, fetchone_results=[
        {"id": 1, "titulo": "Título", "prompt": "x", "creada": None, "actualizada": None,
         "archivada": False, "creada_por": "mama@x.com", "pasos": []},
    ])
    app.dependency_overrides[get_db] = _override_db(cursor)

    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    subapp = FastAPI()

    @subapp.middleware("http")
    async def fake_state(request: Request, call_next):
        request.state.escribe = "papá"
        request.state.creada_por = "papa@x.com"
        return await call_next(request)

    subapp.include_router(historias_api.router)
    subapp.dependency_overrides[get_db] = _override_db(cursor)

    resp = TestClient(subapp).post("/api/historias", json={"prompt": "algo"})

    assert resp.status_code == 201
    assert llamada["escribe"] == "papá"
    app.dependency_overrides.clear()
