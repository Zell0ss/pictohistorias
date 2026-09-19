# scripts/verificar_fase1.py
"""Validación cualitativa de cierre de fase 1: 20 conceptos reales de las
historias de ejemplo (taller del coche + una persona conocida, y cole en autobús)."""
from lib.config import Settings
from lib.db import get_connection
from lib.embeddings import embed_texts
from lib.qdrant_client import get_client
from scripts.buscar_picto import search_picto

CONCEPTOS_DE_PRUEBA = [
    "coche",
    "coche de mamá",
    "coche de papá",
    "taller",
    "mecánico",
    "reparar el coche",
    "Marta",
    "psicomotricidad",
    "autobús",
    "autobús amarillo",
    "conductor de autobús",
    "colegio",
    "cole del Roble",
    "profesora",
    "mamá",
    "papá",
    "ir al cole",
    "volver a casa",
    "niños",
    "compañeros de clase",
]


def main() -> None:
    settings = Settings()
    qdrant = get_client(settings.qdrant_url)

    def embed_fn(texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, api_key=settings.openai_api_key)

    for concepto in CONCEPTOS_DE_PRUEBA:
        resultados = search_picto(concepto, qdrant, settings.qdrant_collection, embed_fn, top=3)
        print(f"\n=== {concepto} ===")
        for r in resultados:
            print(f"  {r['id']:>6}  {r['score']:.3f}  {', '.join(r['keywords'])}")

    # Chequeo de paridad MariaDB <-> Qdrant: este fallo (MariaDB poblado,
    # Qdrant vacío o desincronizado) ya ocurrió una vez durante la tarea 10.
    db_conn = get_connection(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM picto")
        db_count = cursor.fetchone()["n"]

    qdrant_count = qdrant.get_collection(settings.qdrant_collection).points_count

    estado = "✓ coinciden" if db_count == qdrant_count else "✗ NO coinciden — revisar ingesta"
    print(f"\nMariaDB: {db_count} pictos · Qdrant: {qdrant_count} puntos · {estado}")


if __name__ == "__main__":
    main()
