import json

from lib.normalize import normalize_concepto


def find_diccionario_match(conn, conceptos_normalizados: list[str]) -> dict | None:
    conceptos_set = {normalize_concepto(c) for c in conceptos_normalizados}
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM diccionario")
        rows = cursor.fetchall()

    for row in rows:
        candidatos_fila = {normalize_concepto(row["concepto"])}
        for alias in json.loads(row["alias"] or "[]"):
            candidatos_fila.add(normalize_concepto(alias))
        if candidatos_fila & conceptos_set:
            return row
    return None


def list_diccionario(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM diccionario ORDER BY creado DESC")
        rows = cursor.fetchall()
    for row in rows:
        row["alias"] = json.loads(row["alias"] or "[]")
        row["opciones"] = json.loads(row["opciones"]) if row["opciones"] else None
    return rows


def get_diccionario_entry(conn, entry_id: int) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM diccionario WHERE id = %s", (entry_id,))
        row = cursor.fetchone()
    if row is not None:
        row["alias"] = json.loads(row["alias"] or "[]")
        row["opciones"] = json.loads(row["opciones"]) if row["opciones"] else None
    return row


def create_diccionario_entry(
    conn, concepto: str, tipo: str, alias: list[str] | None = None,
    picto_id: int | None = None, foto_path: str | None = None, opciones: dict | None = None,
) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO diccionario (concepto, alias, tipo, picto_id, foto_path, opciones)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                concepto,
                json.dumps(alias or []),
                tipo,
                picto_id,
                foto_path,
                json.dumps(opciones) if opciones else None,
            ),
        )
        return cursor.lastrowid


def update_diccionario_entry(conn, entry_id: int, fields: dict) -> None:
    # fields.keys() viene siempre de DiccionarioPatch (pydantic), nunca de
    # claves arbitrarias del usuario — mismo patrón que update_historia/update_paso.
    if not fields:
        return
    campos_json = {"alias", "opciones"}
    valores = {}
    for k, v in fields.items():
        valores[k] = json.dumps(v) if k in campos_json and v is not None else v
    columnas = ", ".join(f"{k} = %s" for k in valores)
    with conn.cursor() as cursor:
        cursor.execute(f"UPDATE diccionario SET {columnas} WHERE id = %s", [*valores.values(), entry_id])


def delete_diccionario_entry(conn, entry_id: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM diccionario WHERE id = %s", (entry_id,))


def find_diccionario_by_concepto_exacto(conn, concepto: str) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM diccionario WHERE concepto = %s", (concepto,))
        return cursor.fetchone()
