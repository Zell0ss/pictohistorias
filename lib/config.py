from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str = "pictohistorias_db"

    openai_api_key: str
    anthropic_api_key: str | None = None

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "arasaac_es"

    arasaac_locale: str = "es"
    arasaac_api_base: str = "https://api.arasaac.org/api"
    arasaac_static_base: str = "https://static.arasaac.org"
    fotos_dir: str = "fotos"
    nombre_nino: str = ""

    cloudflare_team: str = ""
    cloudflare_access_aud: str = ""
    usuarios_mapa: str = ""

    logcentral_log_dir: str = "logs"
