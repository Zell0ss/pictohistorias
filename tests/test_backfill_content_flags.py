import json

from scripts.backfill_content_flags import (
    backfill_mariadb,
    backfill_qdrant,
    group_by_flags,
    load_flags_from_snapshot,
)


def test_load_flags_from_snapshot_maps_id_and_flags(tmp_path):
    snapshot = {
        "fetched_at": "2026-01-01T00:00:00Z",
        "pictograms": [
            {"_id": 1, "schematic": False, "sex": False, "violence": False},
            {"_id": 2, "schematic": True, "sex": True, "violence": False},
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot))

    flags = load_flags_from_snapshot(str(path))

    assert flags == [
        {"id": 1, "schematic": False, "sex": False, "violence": False},
        {"id": 2, "schematic": True, "sex": True, "violence": False},
    ]


def test_load_flags_from_snapshot_defaults_missing_fields(tmp_path):
    snapshot = {"pictograms": [{"_id": 5}]}
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot))

    flags = load_flags_from_snapshot(str(path))

    assert flags == [{"id": 5, "schematic": False, "sex": False, "violence": False}]


def test_group_by_flags_groups_matching_tuples():
    flags = [
        {"id": 1, "schematic": False, "sex": False, "violence": False},
        {"id": 2, "schematic": False, "sex": False, "violence": False},
        {"id": 3, "schematic": True, "sex": False, "violence": False},
    ]

    groups = group_by_flags(flags)

    assert groups[(False, False, False)] == [1, 2]
    assert groups[(True, False, False)] == [3]
    assert len(groups) == 2


class FakeCursor:
    def __init__(self):
        self.executemany_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def executemany(self, sql, params):
        self.executemany_calls.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj


def test_backfill_mariadb_runs_executemany_with_sex_violence_id():
    conn = FakeConnection()
    flags = [
        {"id": 1, "schematic": False, "sex": True, "violence": False},
        {"id": 2, "schematic": False, "sex": False, "violence": True},
    ]

    count = backfill_mariadb(conn, flags)

    assert count == 2
    sql, params = conn.cursor_obj.executemany_calls[0]
    assert "UPDATE picto SET sex" in sql
    assert params == [(True, False, 1), (False, True, 2)]


class FakeQdrantClient:
    def __init__(self):
        self.set_payload_calls = []

    def set_payload(self, collection_name, payload, points):
        self.set_payload_calls.append((collection_name, payload, points))


def test_backfill_qdrant_groups_by_flag_tuple():
    qdrant = FakeQdrantClient()
    flags = [
        {"id": 1, "schematic": False, "sex": False, "violence": False},
        {"id": 2, "schematic": False, "sex": False, "violence": False},
        {"id": 3, "schematic": True, "sex": False, "violence": False},
    ]

    n_groups = backfill_qdrant(qdrant, "arasaac_es", flags)

    assert n_groups == 2
    calls_by_payload = {tuple(sorted(p.items())): pts for _, p, pts in qdrant.set_payload_calls}
    assert calls_by_payload[(("schematic", False), ("sex", False), ("violence", False))] == [1, 2]
    assert calls_by_payload[(("schematic", True), ("sex", False), ("violence", False))] == [3]
