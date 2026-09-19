import argparse
import json
from collections import defaultdict

from lib.config import Settings
from lib.db import get_connection
from lib.qdrant_client import get_client

_UPDATE_FLAGS_SQL = "UPDATE picto SET sex = %s, violence = %s WHERE id = %s"


def load_flags_from_snapshot(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return [
        {
            "id": p["_id"],
            "schematic": bool(p.get("schematic", False)),
            "sex": bool(p.get("sex", False)),
            "violence": bool(p.get("violence", False)),
        }
        for p in data["pictograms"]
    ]


def group_by_flags(flags: list[dict]) -> dict[tuple[bool, bool, bool], list[int]]:
    groups: dict[tuple[bool, bool, bool], list[int]] = defaultdict(list)
    for f in flags:
        key = (f["schematic"], f["sex"], f["violence"])
        groups[key].append(f["id"])
    return groups


def backfill_mariadb(conn, flags: list[dict]) -> int:
    params = [(f["sex"], f["violence"], f["id"]) for f in flags]
    with conn.cursor() as cursor:
        cursor.executemany(_UPDATE_FLAGS_SQL, params)
    return len(params)


def backfill_qdrant(qdrant_client, collection: str, flags: list[dict]) -> int:
    groups = group_by_flags(flags)
    for (schematic, sex, violence), ids in groups.items():
        qdrant_client.set_payload(
            collection_name=collection,
            payload={"schematic": schematic, "sex": sex, "violence": violence},
            points=ids,
        )
    return len(groups)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill de schematic/sex/violence en MariaDB y Qdrant desde el snapshot cacheado"
    )
    parser.add_argument("--snapshot", default="cache/arasaac_all_es.json")
    args = parser.parse_args()

    settings = Settings()
    flags = load_flags_from_snapshot(args.snapshot)

    conn = get_connection(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    n_rows = backfill_mariadb(conn, flags)
    print(f"MariaDB: {n_rows} pictos actualizados")

    qdrant = get_client(settings.qdrant_url)
    n_groups = backfill_qdrant(qdrant, settings.qdrant_collection, flags)
    print(f"Qdrant: {n_groups} grupos de payload aplicados sobre {len(flags)} puntos")


if __name__ == "__main__":
    main()
