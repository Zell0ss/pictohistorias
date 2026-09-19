def normalize_picto(raw: dict) -> dict:
    return {
        "id": raw["_id"],
        "keywords": raw.get("keywords", []),
        "categories": raw.get("categories") or [],
        "tags": raw.get("tags") or [],
        "descripcion": raw.get("desc") or "",
        "schematic": bool(raw.get("schematic", False)),
        "cacheado": False,
    }


def build_embedding_text(picto: dict) -> str:
    parts = []
    for kw in picto.get("keywords", []):
        word = kw.get("keyword", "")
        meaning = kw.get("meaning", "")
        fragment = f"{word} {meaning}".strip()
        if fragment:
            parts.append(fragment)

    descripcion = picto.get("descripcion", "")
    if descripcion:
        parts.append(descripcion)

    return ". ".join(parts)
