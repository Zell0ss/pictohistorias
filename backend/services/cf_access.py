import jwt
from jwt import PyJWKClient

_jwks_clients: dict[str, PyJWKClient] = {}


def _get_jwks_client(team: str) -> PyJWKClient:
    if team not in _jwks_clients:
        _jwks_clients[team] = PyJWKClient(f"https://{team}.cloudflareaccess.com/cdn-cgi/access/certs")
    return _jwks_clients[team]


def verify_access_jwt(token: str, team: str, aud: str | None = None) -> dict:
    jwks_client = _get_jwks_client(team)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    # verify_aud se activa solo si se pasa aud: sin un audience esperado,
    # PyJWT exigiría uno igualmente y fallaría siempre con audience=None.
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=aud,
        options={"verify_aud": bool(aud)},
    )


def parse_usuarios_mapa(raw: str) -> dict[str, str]:
    mapa = {}
    for par in raw.split(","):
        par = par.strip()
        if not par:
            continue
        email, _, etiqueta = par.partition(":")
        email = email.strip().lower()
        etiqueta = etiqueta.strip()
        if email and etiqueta:
            mapa[email] = etiqueta
    return mapa
