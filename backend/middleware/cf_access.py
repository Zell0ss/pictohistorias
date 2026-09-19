# backend/middleware/cf_access.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.clients import settings
from backend.services.cf_access import parse_usuarios_mapa, verify_access_jwt
from lib.log import get_logger

logger = get_logger("pictohistorias")


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.escribe = "mamá"
        request.state.creada_por = None

        if "cf-connecting-ip" not in request.headers:
            return await call_next(request)

        token = request.headers.get("cf-access-jwt-assertion")
        if not token:
            logger.error("Peticion por el tunel sin Cf-Access-Jwt-Assertion")
            return JSONResponse({"detail": "No autorizado"}, status_code=403)

        try:
            claims = verify_access_jwt(
                token, settings.cloudflare_team, settings.cloudflare_access_aud or None,
            )
        except Exception as exc:
            logger.error("JWT de Cloudflare Access invalido: {}", exc)
            return JSONResponse({"detail": "No autorizado"}, status_code=403)

        if not settings.cloudflare_access_aud:
            aud_recibido = claims.get("aud")
            if isinstance(aud_recibido, list):
                aud_recibido = aud_recibido[0] if aud_recibido else None
            logger.warning(
                "CLOUDFLARE_ACCESS_AUD no configurado; aud del JWT recibido: {} - peagalo en .env",
                aud_recibido,
            )

        email = claims.get("email") or request.headers.get("cf-access-authenticated-user-email")
        if email:
            email = email.lower()
            mapa = parse_usuarios_mapa(settings.usuarios_mapa)
            request.state.escribe = mapa.get(email, "mamá")
            request.state.creada_por = email

        return await call_next(request)
