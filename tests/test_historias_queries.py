import json

from backend.db.queries.historias import (
    create_historia_con_pasos,
    get_historia_con_pasos,
    get_paso,
    list_historias,
    update_historia,
    update_paso,
)


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None, lastrowid=None):
        self.executed = []
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.lastrowid = lastrowid

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetchone_results.pop(0) if self._fetchone_results else None

    def fetchall(self):
        return self._fetchall_results.pop(0) if self._fetchall_results else []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_create_historia_con_pasos_inserts_historia_and_pasos_in_order():
    cursor = FakeCursor(lastrowid=42)
    conn = FakeConnection(cursor)
    pasos = [
        {
            "frase": "Subo al coche", "concepto": "coche", "imagen_tipo": "picto", "picto_id": 1,
            "candidatos": [{"id": 1, "schematic": False}, {"id": 2, "schematic": False}],
            "candidatos_concepto": ["vehiculo", "transporte"],
            "concepto_ganador": "coche", "score_ganador": 0.85,
        },
        {
            "frase": "Llegamos", "concepto": "casa", "imagen_tipo": "picto", "picto_id": None,
            "candidatos": [], "candidatos_concepto": [], "concepto_ganador": None, "score_ganador": None,
        },
    ]

    historia_id = create_historia_con_pasos(conn, "Mi historia", "texto original", pasos)

    assert historia_id == 42
    assert len(cursor.executed) == 3
    assert "INSERT INTO historia" in cursor.executed[0][0]
    assert cursor.executed[0][1] == ("Mi historia", "texto original", None)
    assert "INSERT INTO paso" in cursor.executed[1][0]
    assert cursor.executed[1][1][0] == 42
    assert cursor.executed[1][1][1] == 1
    assert json.loads(cursor.executed[1][1][7]) == [{"id": 1, "schematic": False}, {"id": 2, "schematic": False}]
    assert json.loads(cursor.executed[1][1][8]) == ["vehiculo", "transporte"]
    assert cursor.executed[1][1][9] == "coche"
    assert cursor.executed[1][1][10] == 0.85


def test_get_historia_con_pasos_assembles_result_with_parsed_candidatos():
    historia_row = {"id": 5, "titulo": "T", "prompt": "P", "archivada": False}
    pasos_rows = [{"id": 1, "historia_id": 5, "orden": 1, "candidatos": "[1, 2]",
                   "candidatos_concepto": '["vehiculo","transporte"]'}]
    cursor = FakeCursor(fetchone_results=[historia_row], fetchall_results=[pasos_rows])
    conn = FakeConnection(cursor)

    resultado = get_historia_con_pasos(conn, 5)

    assert resultado["id"] == 5
    assert resultado["pasos"][0]["candidatos"] == [1, 2]
    assert resultado["pasos"][0]["candidatos_concepto"] == ["vehiculo", "transporte"]


def test_get_historia_con_pasos_returns_none_when_missing():
    cursor = FakeCursor(fetchone_results=[None])
    conn = FakeConnection(cursor)

    assert get_historia_con_pasos(conn, 999) is None


def test_list_historias_filters_archivada_in_sql():
    cursor = FakeCursor(fetchall_results=[[{"id": 1, "titulo": "T"}]])
    conn = FakeConnection(cursor)

    resultado = list_historias(conn)

    assert resultado == [{"id": 1, "titulo": "T"}]
    assert "archivada = FALSE" in cursor.executed[0][0]


def test_update_historia_builds_dynamic_set_clause():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_historia(conn, 7, {"titulo": "Nuevo", "archivada": True})

    sql, params = cursor.executed[0]
    assert "titulo = %s" in sql
    assert "archivada = %s" in sql
    assert params == ["Nuevo", True, 7]


def test_update_historia_noop_on_empty_fields():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_historia(conn, 7, {})

    assert cursor.executed == []


def test_get_paso_parses_candidatos():
    cursor = FakeCursor(fetchone_results=[{"id": 3, "candidatos": "[9]", "candidatos_concepto": '["vehiculo"]'}])
    conn = FakeConnection(cursor)

    paso = get_paso(conn, 3)

    assert paso["candidatos"] == [9]
    assert paso["candidatos_concepto"] == ["vehiculo"]


def test_update_paso_builds_dynamic_set_clause():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_paso(conn, 11, {"frase": "Nueva frase"})

    sql, params = cursor.executed[0]
    assert "frase = %s" in sql
    assert params == ["Nueva frase", 11]


def test_create_historia_con_pasos_guarda_creada_por():
    cursor = FakeCursor(lastrowid=1)
    conn = FakeConnection(cursor)

    create_historia_con_pasos(conn, "Título", "prompt", [], creada_por="mama@x.com")

    sql, params = cursor.executed[0]
    assert "creada_por" in sql
    assert params[-1] == "mama@x.com" or "mama@x.com" in params


def test_create_historia_con_pasos_creada_por_por_defecto_none():
    cursor = FakeCursor(lastrowid=1)
    conn = FakeConnection(cursor)

    create_historia_con_pasos(conn, "Título", "prompt", [])

    sql, params = cursor.executed[0]
    assert None in params
