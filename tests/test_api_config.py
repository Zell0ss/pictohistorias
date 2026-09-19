from fastapi.testclient import TestClient

from backend.clients import settings
from backend.main import app


def test_config_devuelve_el_nombre_configurado(monkeypatch):
    monkeypatch.setattr(settings, "nombre_nino", "  Leo ")

    resp = TestClient(app).get("/api/config")

    assert resp.status_code == 200
    assert resp.json() == {"nombre_nino": "Leo"}


def test_config_por_defecto_no_tiene_nombre(monkeypatch):
    monkeypatch.setattr(settings, "nombre_nino", "")

    resp = TestClient(app).get("/api/config")

    assert resp.json() == {"nombre_nino": ""}
