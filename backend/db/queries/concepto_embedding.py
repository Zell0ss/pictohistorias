import json


def get_cached_embedding(conn, concepto_normalizado: str) -> list[float] | None:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT embedding FROM concepto_embedding WHERE concepto = %s",
            (concepto_normalizado,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return json.loads(row["embedding"])


def set_cached_embedding(conn, concepto_normalizado: str, embedding: list[float]) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO concepto_embedding (concepto, embedding)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE embedding = VALUES(embedding)
            """,
            (concepto_normalizado, json.dumps(embedding)),
        )
