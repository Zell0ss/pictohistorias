from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

import backend.services.resolucion as resolucion_module
from lib.qdrant_client import ensure_collection, upsert_pictos


def _setup_qdrant():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_col", vector_size=3)
    points = [
        PointStruct(
            id=1, vector=[1.0, 0.0, 0.0],
            payload={"id": 1, "keywords": [{"keyword": "coche detenido"}], "categories": [], "tags": [],
                     "schematic": False, "sex": False, "violence": False},
        ),
        PointStruct(
            id=2, vector=[0.95, 0.05, 0.0],
            payload={"id": 2, "keywords": [{"keyword": "coche generico"}], "categories": [], "tags": [],
                     "schematic": False, "sex": False, "violence": False},
        ),
        PointStruct(
            id=3, vector=[0.0, 1.0, 0.0],
            payload={"id": 3, "keywords": [{"keyword": "taller"}], "categories": [], "tags": [],
                     "schematic": False, "sex": False, "violence": False},
        ),
    ]
    upsert_pictos(client, "test_col", points)
    return client


def _fake_get_or_embed(vectors_by_term):
    def _fn(conn, term, embed_fn):
        return vectors_by_term[term]
    return _fn


def _fake_no_exact_match(indice, concepto):
    return []


def test_resolve_paso_imagen_uses_diccionario_match_first(monkeypatch):
    monkeypatch.setattr(
        resolucion_module, "find_diccionario_match",
        lambda conn, normalizados: {"tipo": "picto", "picto_id": 99, "foto_path": None},
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=object(), collection="x", embed_fn=None,
        concepto="coche de mama", candidatos_concepto=["coche"],
    )

    assert resultado == {
        "imagen_tipo": "picto", "picto_id": 99, "foto_path": None,
        "candidatos": [], "concepto_ganador": None, "score_ganador": None, "via": "diccionario",
    }


def test_resolve_paso_imagen_uses_exact_match_on_principal_before_qdrant(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {"taller": [39586]})

    def _fail_if_called(*a, **k):
        raise AssertionError("no deberia llamar a Qdrant ni a embeddings si hay match exacto")

    monkeypatch.setattr(resolucion_module, "get_or_embed_concepto", _fail_if_called)

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=object(), collection="test_col", embed_fn=None,
        concepto="taller", candidatos_concepto=["reparar el coche", "mecanico"],
    )

    assert resultado["via"] == "exacta"
    assert resultado["picto_id"] == 39586
    assert resultado["concepto_ganador"] == "taller"
    assert resultado["score_ganador"] == 1.0
    assert resultado["candidatos"] == [{"id": 39586, "schematic": False}]


def test_resolve_paso_imagen_uses_principal_when_above_threshold_with_schematic_appended(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {})
    client = _setup_qdrant()
    # add one schematic point that only shows up when exclude_flagged=False
    from qdrant_client.models import PointStruct as PS
    client.upsert(collection_name="test_col", points=[
        PS(id=4, vector=[0.0, 0.99, 0.01],
           payload={"id": 4, "keywords": [{"keyword": "taller esquematico"}], "categories": [], "tags": [],
                    "schematic": True, "sex": False, "violence": False}),
        # sex-flagged schematic at a similar score: must NOT be appended to candidatos
        PS(id=5, vector=[0.0, 0.98, 0.02],
           payload={"id": 5, "keywords": [{"keyword": "taller esquematico sexual"}], "categories": [], "tags": [],
                    "schematic": True, "sex": True, "violence": False}),
    ])
    monkeypatch.setattr(
        resolucion_module, "get_or_embed_concepto",
        _fake_get_or_embed({"taller": [0.0, 1.0, 0.0]}),
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=client, collection="test_col", embed_fn=None,
        concepto="taller", candidatos_concepto=["reparar el coche", "mecanico"],
    )

    assert resultado["picto_id"] == 3
    assert resultado["via"] == "principal"
    assert resultado["concepto_ganador"] == "taller"
    assert resultado["score_ganador"] == 1.0
    ids_normales = [c["id"] for c in resultado["candidatos"] if not c["schematic"]]
    ids_esquematicos = [c["id"] for c in resultado["candidatos"] if c["schematic"]]
    assert 3 in ids_normales
    assert ids_esquematicos == [4]
    assert 5 not in [c["id"] for c in resultado["candidatos"]]


def test_resolve_paso_imagen_falls_back_to_candidato_when_principal_below_threshold(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {})
    client = _setup_qdrant()
    monkeypatch.setattr(
        resolucion_module, "get_or_embed_concepto",
        _fake_get_or_embed({
            "taller": [0.0, 1.0, 0.0],  # unused here, principal is "coche de mama" in this test
            "coche de mama": [0.6, 0.0, 0.8],
            "reparar el coche": [0.6, 0.0, 0.8],
            "mecanico": [0.5, 0.0, 0.8660254],
            "coche": [1.0, 0.0, 0.0],
        }),
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=client, collection="test_col", embed_fn=None,
        concepto="coche de mama", candidatos_concepto=["coche"],
    )

    assert resultado["via"] == "candidato"
    assert resultado["picto_id"] == 1
    assert resultado["concepto_ganador"] == "coche"
    assert resultado["score_ganador"] == 1.0


def test_resolve_paso_imagen_returns_sin_imagen_when_nothing_clears_threshold(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {})
    client = _setup_qdrant()
    monkeypatch.setattr(
        resolucion_module, "get_or_embed_concepto",
        _fake_get_or_embed({"esperar": [-0.6, 0.0, 0.8], "aguardar": [-0.5, 0.0, 0.8660254]}),
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=client, collection="test_col", embed_fn=None,
        concepto="esperar", candidatos_concepto=["aguardar"],
    )

    assert resultado["via"] == "sin_imagen"
    assert resultado["picto_id"] is None
    assert resultado["concepto_ganador"] == "esperar"
    assert resultado["score_ganador"] == 0.0
    assert len(resultado["candidatos"]) == 3


def test_resolve_paso_imagen_uses_exact_match_on_candidato_when_principal_fails(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {"taller": [39586]})
    client = _setup_qdrant()
    monkeypatch.setattr(
        resolucion_module, "get_or_embed_concepto",
        _fake_get_or_embed({"coche de mama": [0.6, 0.0, 0.8]}),
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=client, collection="test_col", embed_fn=None,
        concepto="coche de mama", candidatos_concepto=["taller"],
    )

    assert resultado["via"] == "exacta"
    assert resultado["picto_id"] == 39586
    assert resultado["concepto_ganador"] == "taller"
    assert resultado["score_ganador"] == 1.0
    assert resultado["candidatos"] == [{"id": 39586, "schematic": False}]


def test_resolve_paso_imagen_skips_exact_match_on_capitalized_principal(monkeypatch):
    monkeypatch.setattr(resolucion_module, "find_diccionario_match", lambda conn, normalizados: None)
    monkeypatch.setattr(resolucion_module, "get_index", lambda conn: {"marta": [7301]})
    client = _setup_qdrant()
    monkeypatch.setattr(
        resolucion_module, "get_or_embed_concepto",
        _fake_get_or_embed({"Marta": [0.0, 1.0, 0.0]}),
    )

    resultado = resolucion_module.resolve_paso_imagen(
        conn=object(), qdrant_client=client, collection="test_col", embed_fn=None,
        concepto="Marta", candidatos_concepto=["psicomotricista", "jugar"],
    )

    assert resultado["via"] != "exacta"
    assert resultado["via"] == "principal"
    assert resultado["picto_id"] == 3
    assert resultado["concepto_ganador"] == "Marta"
