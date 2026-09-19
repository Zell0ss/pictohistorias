# backend/clients.py
import anthropic

from lib.config import Settings
from lib.embeddings import embed_texts
from lib.qdrant_client import get_client

settings = Settings()

if not settings.anthropic_api_key:
    raise RuntimeError("ANTHROPIC_API_KEY no configurado en .env")

qdrant_client = get_client(settings.qdrant_url)
anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def embed_fn(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts, api_key=settings.openai_api_key)
