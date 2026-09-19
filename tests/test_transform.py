from lib.transform import build_embedding_text, normalize_picto

RAW_COCHE = {
    "_id": 2339,
    "keywords": [
        {"keyword": "coche", "meaning": "Vehículo con motor de cuatro ruedas", "plural": "coches", "type": 2},
        {"keyword": "automóvil", "meaning": "por antonomasia coche", "plural": "automóviles", "type": 2},
    ],
    "categories": ["land transport", "road safety"],
    "tags": ["movement", "traffic"],
    "desc": "",
    "schematic": False,
}


def test_normalize_picto_maps_fields():
    result = normalize_picto(RAW_COCHE)

    assert result == {
        "id": 2339,
        "keywords": RAW_COCHE["keywords"],
        "categories": ["land transport", "road safety"],
        "tags": ["movement", "traffic"],
        "descripcion": "",
        "schematic": False,
        "cacheado": False,
    }


def test_normalize_picto_defaults_missing_lists():
    raw = {"_id": 5, "keywords": [{"keyword": "x", "meaning": "y"}]}

    result = normalize_picto(raw)

    assert result["categories"] == []
    assert result["tags"] == []
    assert result["descripcion"] == ""
    assert result["schematic"] is False


def test_build_embedding_text_joins_keywords_and_meanings():
    picto = normalize_picto(RAW_COCHE)

    text = build_embedding_text(picto)

    assert "coche" in text
    assert "Vehículo con motor de cuatro ruedas" in text
    assert "automóvil" in text


def test_build_embedding_text_includes_descripcion_when_present():
    picto = normalize_picto(RAW_COCHE)
    picto["descripcion"] = "un coche de juguete"

    text = build_embedding_text(picto)

    assert "un coche de juguete" in text
