import json

from backend.db.queries.diccionario import (
    create_diccionario_entry,
    delete_diccionario_entry,
    find_diccionario_by_concepto_exacto,
    find_diccionario_match,
    get_diccionario_entry,
    list_diccionario,
    update_diccionario_entry,
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


def test_find_diccionario_match_by_concepto():
    rows = [
        {"concepto": "coche de mamá", "alias": "[]", "tipo": "picto", "picto_id": 5, "foto_path": None},
    ]
    conn = FakeConnection(FakeCursor(fetchall_results=[rows]))

    match = find_diccionario_match(conn, ["coche de mama", "coche"])

    assert match["picto_id"] == 5


def test_find_diccionario_match_by_alias():
    rows = [
        {"concepto": "Marta", "alias": '["la seño Marta", "seño"]', "tipo": "foto", "picto_id": None, "foto_path": "fotos/1.jpg"},
    ]
    conn = FakeConnection(FakeCursor(fetchall_results=[rows]))

    match = find_diccionario_match(conn, ["seño"])

    assert match["foto_path"] == "fotos/1.jpg"


def test_find_diccionario_match_returns_none_when_no_match():
    rows = [
        {"concepto": "coche de mamá", "alias": "[]", "tipo": "picto", "picto_id": 5, "foto_path": None},
    ]
    conn = FakeConnection(FakeCursor(fetchall_results=[rows]))

    assert find_diccionario_match(conn, ["taller"]) is None


def test_find_diccionario_match_normalizes_accents_and_case():
    rows = [
        {"concepto": "Cole del Roble", "alias": "[]", "tipo": "picto", "picto_id": 7, "foto_path": None},
    ]
    conn = FakeConnection(FakeCursor(fetchall_results=[rows]))

    match = find_diccionario_match(conn, ["cole del roble"])

    assert match["picto_id"] == 7


# New tests for CRUD operations

def test_list_diccionario_parses_alias_and_opciones():
    rows = [
        {"id": 1, "concepto": "coche de mamá", "alias": '["coche negro"]', "tipo": "picto",
         "picto_id": 5, "foto_path": None, "opciones": None},
    ]
    conn = FakeConnection(FakeCursor(fetchall_results=[rows]))

    resultado = list_diccionario(conn)

    assert resultado[0]["alias"] == ["coche negro"]
    assert resultado[0]["opciones"] is None


def test_get_diccionario_entry_returns_none_when_missing():
    conn = FakeConnection(FakeCursor(fetchone_results=[None]))

    assert get_diccionario_entry(conn, 999) is None


def test_get_diccionario_entry_parses_opciones_when_present():
    row = {"id": 2, "concepto": "Marta", "alias": "[]", "tipo": "foto",
           "picto_id": None, "foto_path": "fotos/x.jpg", "opciones": '{"skin": "#f7d9c4"}'}
    conn = FakeConnection(FakeCursor(fetchone_results=[row]))

    resultado = get_diccionario_entry(conn, 2)

    assert resultado["opciones"] == {"skin": "#f7d9c4"}


def test_create_diccionario_entry_inserts_serialized_json():
    cursor = FakeCursor(lastrowid=7)
    conn = FakeConnection(cursor)

    entry_id = create_diccionario_entry(
        conn, concepto="taller", tipo="picto", alias=["garaje"], picto_id=39586,
    )

    assert entry_id == 7
    sql, params = cursor.executed[0]
    assert "INSERT INTO diccionario" in sql
    assert params[0] == "taller"
    assert json.loads(params[1]) == ["garaje"]


def test_update_diccionario_entry_serializes_alias_and_opciones():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_diccionario_entry(conn, 3, {"alias": ["x", "y"], "opciones": {"hair": "#000"}})

    sql, params = cursor.executed[0]
    assert "alias = %s" in sql
    assert "opciones = %s" in sql
    valores = list(params)
    assert json.loads(valores[0]) == ["x", "y"]
    assert json.loads(valores[1]) == {"hair": "#000"}


def test_update_diccionario_entry_leaves_non_json_fields_untouched():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_diccionario_entry(conn, 3, {"concepto": "nuevo nombre"})

    sql, params = cursor.executed[0]
    assert params[0] == "nuevo nombre"


def test_update_diccionario_entry_noop_on_empty_fields():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    update_diccionario_entry(conn, 3, {})

    assert cursor.executed == []


def test_delete_diccionario_entry_deletes_by_id():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    delete_diccionario_entry(conn, 9)

    sql, params = cursor.executed[0]
    assert "DELETE FROM diccionario" in sql
    assert params == (9,)


def test_find_diccionario_by_concepto_exacto_matches_literal_string():
    row = {"id": 1, "concepto": "taller"}
    conn = FakeConnection(FakeCursor(fetchone_results=[row]))

    assert find_diccionario_by_concepto_exacto(conn, "taller")["id"] == 1


def test_find_diccionario_by_concepto_exacto_returns_none_when_missing():
    conn = FakeConnection(FakeCursor(fetchone_results=[None]))

    assert find_diccionario_by_concepto_exacto(conn, "no existe") is None
