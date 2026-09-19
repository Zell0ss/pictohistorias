import json

import backend.services.exact_match as exact_match_module
from backend.services.exact_match import build_index, find_exact_match_in_index, get_index


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, rows):
        self._cursor = FakeCursor(rows)

    def cursor(self):
        return self._cursor


def test_build_index_maps_normalized_keyword_to_picto_ids():
    conn = FakeConnection([
        {"id": 2339, "keywords": json.dumps([{"keyword": "coche"}, {"keyword": "automóvil"}])},
        {"id": 3082, "keywords": json.dumps([{"keyword": "colegio"}])},
    ])

    indice = build_index(conn)

    assert indice["coche"] == [2339]
    assert indice["automovil"] == [2339]
    assert indice["colegio"] == [3082]


def test_build_index_accumulates_multiple_ids_for_same_keyword():
    conn = FakeConnection([
        {"id": 2262, "keywords": json.dumps([{"keyword": "autobús"}])},
        {"id": 2263, "keywords": json.dumps([{"keyword": "autobús"}])},
    ])

    indice = build_index(conn)

    assert indice["autobus"] == [2262, 2263]


def test_find_exact_match_in_index_direct_hit():
    indice = {"coche": [2339]}

    assert find_exact_match_in_index(indice, "Coche") == [2339]


def test_find_exact_match_in_index_tries_singular_form():
    indice = {"autobus": [2262, 2263]}

    assert find_exact_match_in_index(indice, "autobuses") == [2262, 2263]


def test_find_exact_match_in_index_returns_empty_when_no_match():
    indice = {"coche": [2339]}

    assert find_exact_match_in_index(indice, "bicicleta") == []


def test_get_index_caches_after_first_call(monkeypatch):
    exact_match_module._INDICE = None  # reset module-level cache for test isolation
    build_calls = []

    def fake_build_index(conn):
        build_calls.append(conn)
        return {"coche": [2339]}

    monkeypatch.setattr(exact_match_module, "build_index", fake_build_index)

    get_index(conn=object())
    get_index(conn=object())

    assert len(build_calls) == 1
