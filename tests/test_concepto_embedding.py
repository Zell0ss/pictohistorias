import json

from backend.db.queries.concepto_embedding import get_cached_embedding, set_cached_embedding


class FakeCursor:
    def __init__(self, fetchone_result=None):
        self.executed = []
        self._fetchone_result = fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetchone_result


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_get_cached_embedding_returns_none_when_missing():
    conn = FakeConnection(FakeCursor(fetchone_result=None))

    assert get_cached_embedding(conn, "coche") is None


def test_get_cached_embedding_parses_stored_json():
    row = {"embedding": json.dumps([0.1, 0.2, 0.3])}
    conn = FakeConnection(FakeCursor(fetchone_result=row))

    assert get_cached_embedding(conn, "coche") == [0.1, 0.2, 0.3]


def test_set_cached_embedding_upserts_with_serialized_json():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)

    set_cached_embedding(conn, "coche", [0.1, 0.2])

    sql, params = cursor.executed[0]
    assert "INSERT INTO concepto_embedding" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params[0] == "coche"
    assert json.loads(params[1]) == [0.1, 0.2]
