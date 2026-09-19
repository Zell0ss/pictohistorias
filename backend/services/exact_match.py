import json

from lib.normalize import formas_singulares, normalize_concepto

_INDICE: dict[str, list[int]] | None = None


def build_index(conn) -> dict[str, list[int]]:
    indice: dict[str, list[int]] = {}
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, keywords FROM picto WHERE schematic = 0 AND sex = 0 AND violence = 0 ORDER BY id"
        )
        rows = cursor.fetchall()
    for row in rows:
        for kw in json.loads(row["keywords"] or "[]"):
            palabra = kw.get("keyword")
            if not palabra:
                continue
            clave = normalize_concepto(palabra)
            indice.setdefault(clave, []).append(row["id"])
    return indice


def find_exact_match_in_index(indice: dict[str, list[int]], concepto: str) -> list[int]:
    normalizado = normalize_concepto(concepto)
    for forma in formas_singulares(normalizado):
        ids = indice.get(forma)
        if ids:
            return ids
    return []


def get_index(conn) -> dict[str, list[int]]:
    global _INDICE
    if _INDICE is None:
        _INDICE = build_index(conn)
    return _INDICE
