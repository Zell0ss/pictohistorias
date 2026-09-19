from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import backend.middleware.cf_access as cf_access_mw
from backend.middleware.cf_access import CloudflareAccessMiddleware


def _build_app(monkeypatch, team="miequipo", aud="", usuarios_mapa="mama@x.com:mamá,papa@x.com:papá"):
    import backend.clients as clients_mod
    monkeypatch.setattr(clients_mod.settings, "cloudflare_team", team)
    monkeypatch.setattr(clients_mod.settings, "cloudflare_access_aud", aud)
    monkeypatch.setattr(clients_mod.settings, "usuarios_mapa", usuarios_mapa)

    app = FastAPI()
    app.add_middleware(CloudflareAccessMiddleware)

    @app.get("/eco")
    def eco(request: Request):
        return {"escribe": request.state.escribe, "creada_por": request.state.creada_por}

    return TestClient(app)


def test_sin_cabecera_tunel_pasa_sin_autenticar(monkeypatch):
    client = _build_app(monkeypatch)

    resp = client.get("/eco")

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "mamá", "creada_por": None}


def test_con_tunel_sin_jwt_devuelve_403(monkeypatch):
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={"Cf-Connecting-Ip": "1.2.3.4"})

    assert resp.status_code == 403


def test_con_tunel_jwt_invalido_devuelve_403(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: (_ for _ in ()).throw(Exception("invalido")))
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={"Cf-Connecting-Ip": "1.2.3.4", "Cf-Access-Jwt-Assertion": "token-malo"})

    assert resp.status_code == 403


def test_con_tunel_jwt_valido_y_email_mapeado(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"email": "mama@x.com", "aud": ["abc"]})
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "mama@x.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "mamá", "creada_por": "mama@x.com"}


def test_con_tunel_jwt_valido_email_no_mapeado_usa_mama_por_defecto(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"email": "desconocido@x.com"})
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "desconocido@x.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "mamá", "creada_por": "desconocido@x.com"}


def test_con_tunel_jwt_valido_email_con_mayusculas_se_mapea_igual(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"email": "Mama@X.com", "aud": ["abc"]})
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "Mama@X.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "mamá", "creada_por": "mama@x.com"}


def test_email_del_claim_del_jwt_tiene_prioridad_sobre_la_cabecera(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"email": "mama@x.com", "aud": ["abc"]})
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "otra-persona@x.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "mamá", "creada_por": "mama@x.com"}


def test_sin_email_en_claim_usa_la_cabecera_como_fallback(monkeypatch):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"aud": ["abc"]})
    client = _build_app(monkeypatch)

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "papa@x.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {"escribe": "papá", "creada_por": "papa@x.com"}


def test_aud_vacio_no_rompe_y_registra_el_claim(monkeypatch, caplog):
    monkeypatch.setattr(cf_access_mw, "verify_access_jwt", lambda *a, **k: {"email": "mama@x.com", "aud": ["real-aud-123"]})
    client = _build_app(monkeypatch, aud="")

    resp = client.get("/eco", headers={
        "Cf-Connecting-Ip": "1.2.3.4",
        "Cf-Access-Jwt-Assertion": "token-bueno",
        "Cf-Access-Authenticated-User-Email": "mama@x.com",
    })

    assert resp.status_code == 200
