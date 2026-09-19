import json

from lib.db import upsert_picto


class FakeCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj


def test_upsert_picto_runs_insert_with_serialized_json_fields():
    conn = FakeConnection()
    picto = {
        "id": 2339,
        "keywords": [{"keyword": "coche", "meaning": "vehículo"}],
        "categories": ["land transport"],
        "tags": [],
        "descripcion": "",
        "schematic": False,
        "cacheado": False,
    }

    upsert_picto(conn, picto)

    sql, params = conn.cursor_obj.executed[0]
    assert "INSERT INTO picto" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert params["id"] == 2339
    assert json.loads(params["keywords"]) == [{"keyword": "coche", "meaning": "vehículo"}]
    assert json.loads(params["categories"]) == ["land transport"]
    assert params["schematic"] is False


def test_upsert_picto_defaults_missing_categories_and_tags():
    conn = FakeConnection()
    picto = {"id": 1, "keywords": [], "descripcion": "", "schematic": False, "cacheado": False}

    upsert_picto(conn, picto)

    _, params = conn.cursor_obj.executed[0]
    assert json.loads(params["categories"]) == []
    assert json.loads(params["tags"]) == []
