import json


def create_historia_con_pasos(
    conn, titulo: str, prompt: str, pasos: list[dict], creada_por: str | None = None
) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO historia (titulo, prompt, creada_por) VALUES (%s, %s, %s)",
            (titulo, prompt, creada_por),
        )
        historia_id = cursor.lastrowid
        for orden, paso in enumerate(pasos, start=1):
            cursor.execute(
                """
                INSERT INTO paso (
                    historia_id, orden, frase, concepto, imagen_tipo, picto_id, foto_path,
                    candidatos, candidatos_concepto, concepto_ganador, score_ganador
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    historia_id,
                    orden,
                    paso["frase"],
                    paso.get("concepto"),
                    paso["imagen_tipo"],
                    paso.get("picto_id"),
                    paso.get("foto_path"),
                    json.dumps(paso.get("candidatos") or []),
                    json.dumps(paso.get("candidatos_concepto") or []),
                    paso.get("concepto_ganador"),
                    paso.get("score_ganador"),
                ),
            )
    return historia_id


def get_historia_con_pasos(conn, historia_id: int) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM historia WHERE id = %s", (historia_id,))
        historia = cursor.fetchone()
        if historia is None:
            return None
        cursor.execute(
            "SELECT * FROM paso WHERE historia_id = %s ORDER BY orden", (historia_id,)
        )
        pasos = cursor.fetchall()
    for paso in pasos:
        paso["candidatos"] = json.loads(paso["candidatos"] or "[]")
        paso["candidatos_concepto"] = json.loads(paso["candidatos_concepto"] or "[]")
    historia["pasos"] = pasos
    return historia


def list_historias(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, titulo, creada, actualizada FROM historia WHERE archivada = FALSE ORDER BY creada DESC"
        )
        return cursor.fetchall()


def update_historia(conn, historia_id: int, fields: dict) -> None:
    # fields.keys() nunca vienen de input libre: los llama la capa API con las
    # claves fijas de HistoriaPatch (pydantic), nunca claves arbitrarias del usuario.
    if not fields:
        return
    columnas = ", ".join(f"{k} = %s" for k in fields)
    valores = list(fields.values()) + [historia_id]
    with conn.cursor() as cursor:
        cursor.execute(f"UPDATE historia SET {columnas} WHERE id = %s", valores)


def get_paso(conn, paso_id: int) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM paso WHERE id = %s", (paso_id,))
        paso = cursor.fetchone()
    if paso is not None:
        paso["candidatos"] = json.loads(paso["candidatos"] or "[]")
        paso["candidatos_concepto"] = json.loads(paso["candidatos_concepto"] or "[]")
    return paso


def update_paso(conn, paso_id: int, fields: dict) -> None:
    # fields.keys() vienen de PasoPatch (pydantic), mismo razonamiento que update_historia.
    if not fields:
        return
    columnas = ", ".join(f"{k} = %s" for k in fields)
    valores = list(fields.values()) + [paso_id]
    with conn.cursor() as cursor:
        cursor.execute(f"UPDATE paso SET {columnas} WHERE id = %s", valores)
