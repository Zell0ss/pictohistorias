import json

import pymysql
import pymysql.cursors

_UPSERT_PICTO_SQL = """
    INSERT INTO picto (id, keywords, categories, tags, descripcion, schematic, cacheado, actualizado)
    VALUES (%(id)s, %(keywords)s, %(categories)s, %(tags)s, %(descripcion)s, %(schematic)s, %(cacheado)s, NOW())
    ON DUPLICATE KEY UPDATE
        keywords = VALUES(keywords),
        categories = VALUES(categories),
        tags = VALUES(tags),
        descripcion = VALUES(descripcion),
        schematic = VALUES(schematic),
        actualizado = NOW()
    -- cacheado deliberadamente NO se refresca aqui: rastrea si el PNG ya se
    -- descargo a disco local, un hecho que gestiona otro proceso distinto de
    -- la ingesta; refrescarlo aqui borraria el estado real de cache en cada
    -- reingesta.
"""


def get_connection(host: str, port: int, user: str, password: str, database: str):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def upsert_picto(conn, picto: dict) -> None:
    params = {
        "id": picto["id"],
        "keywords": json.dumps(picto.get("keywords") or [], ensure_ascii=False),
        "categories": json.dumps(picto.get("categories") or [], ensure_ascii=False),
        "tags": json.dumps(picto.get("tags") or [], ensure_ascii=False),
        "descripcion": picto.get("descripcion") or "",
        "schematic": bool(picto.get("schematic", False)),
        "cacheado": bool(picto.get("cacheado", False)),
    }
    with conn.cursor() as cursor:
        cursor.execute(_UPSERT_PICTO_SQL, params)
