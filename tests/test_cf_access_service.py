import jwt
import pytest

from backend.services.cf_access import parse_usuarios_mapa, verify_access_jwt


def test_parse_usuarios_mapa_basico():
    resultado = parse_usuarios_mapa("mama@x.com:mamá,papa@x.com:papá")

    assert resultado == {"mama@x.com": "mamá", "papa@x.com": "papá"}


def test_parse_usuarios_mapa_ignora_espacios_y_vacios():
    resultado = parse_usuarios_mapa(" mama@x.com : mamá , , papa@x.com:papá ")

    assert resultado == {"mama@x.com": "mamá", "papa@x.com": "papá"}


def test_parse_usuarios_mapa_cadena_vacia():
    assert parse_usuarios_mapa("") == {}


def test_parse_usuarios_mapa_normaliza_email_a_minusculas():
    resultado = parse_usuarios_mapa("Mama@X.com:mamá,PAPA@x.com:papá")

    assert resultado == {"mama@x.com": "mamá", "papa@x.com": "papá"}


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJWKClient:
    def __init__(self, url):
        self.url = url

    def get_signing_key_from_jwt(self, token):
        return FakeSigningKey("clave-publica-falsa")


def test_verify_access_jwt_devuelve_claims_validos(monkeypatch):
    import backend.services.cf_access as cf_access

    monkeypatch.setattr(cf_access, "PyJWKClient", FakeJWKClient)
    monkeypatch.setattr(
        cf_access.jwt, "decode",
        lambda token, key, algorithms, audience=None, options=None: {"email": "mama@x.com", "aud": ["abc123"]},
    )

    claims = verify_access_jwt("token-falso", "miequipo", aud=None)

    assert claims == {"email": "mama@x.com", "aud": ["abc123"]}


def test_verify_access_jwt_sin_aud_no_lo_exige(monkeypatch):
    import backend.services.cf_access as cf_access

    llamadas = {}
    monkeypatch.setattr(cf_access, "PyJWKClient", FakeJWKClient)

    def fake_decode(token, key, algorithms, audience=None, options=None):
        llamadas["audience"] = audience
        llamadas["options"] = options
        return {"email": "mama@x.com"}

    monkeypatch.setattr(cf_access.jwt, "decode", fake_decode)

    verify_access_jwt("token-falso", "miequipo", aud=None)

    assert llamadas["audience"] is None
    assert llamadas["options"]["verify_aud"] is False


def test_verify_access_jwt_con_aud_lo_exige(monkeypatch):
    import backend.services.cf_access as cf_access

    llamadas = {}
    monkeypatch.setattr(cf_access, "PyJWKClient", FakeJWKClient)

    def fake_decode(token, key, algorithms, audience=None, options=None):
        llamadas["audience"] = audience
        llamadas["options"] = options
        return {"email": "mama@x.com"}

    monkeypatch.setattr(cf_access.jwt, "decode", fake_decode)

    verify_access_jwt("token-falso", "miequipo", aud="abc123")

    assert llamadas["audience"] == "abc123"
    assert llamadas["options"]["verify_aud"] is True


def test_verify_access_jwt_propaga_error_de_firma(monkeypatch):
    import backend.services.cf_access as cf_access

    monkeypatch.setattr(cf_access, "PyJWKClient", FakeJWKClient)

    def fake_decode(*a, **k):
        raise jwt.exceptions.InvalidSignatureError("firma invalida")

    monkeypatch.setattr(cf_access.jwt, "decode", fake_decode)

    with pytest.raises(jwt.exceptions.PyJWTError):
        verify_access_jwt("token-falso", "miequipo", aud=None)
