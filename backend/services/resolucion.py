from backend.db.queries.diccionario import find_diccionario_match
from backend.services.embeddings_cache import get_or_embed_concepto
from backend.services.exact_match import find_exact_match_in_index, get_index
from lib.normalize import normalize_concepto
from lib.qdrant_client import search_pictos

UMBRAL_SIMILITUD = 0.70
MAX_ESQUEMATICOS = 2


def resolve_paso_imagen(
    conn,
    qdrant_client,
    collection: str,
    embed_fn,
    concepto: str,
    candidatos_concepto: list[str],
) -> dict:
    todos_terminos = [concepto] + list(candidatos_concepto)
    normalizados = [normalize_concepto(t) for t in todos_terminos]

    match = find_diccionario_match(conn, normalizados)
    if match is not None:
        return {
            "imagen_tipo": match["tipo"],
            "picto_id": match["picto_id"],
            "foto_path": match["foto_path"],
            "candidatos": [],
            "concepto_ganador": None,
            "score_ganador": None,
            "via": "diccionario",
        }

    indice = get_index(conn)
    if not concepto[:1].isupper():
        exactos_principal = find_exact_match_in_index(indice, concepto)
        if exactos_principal:
            candidatos = [{"id": i, "schematic": False} for i in exactos_principal[:5]]
            return {
                "imagen_tipo": "picto",
                "picto_id": exactos_principal[0],
                "foto_path": None,
                "candidatos": candidatos,
                "concepto_ganador": concepto,
                "score_ganador": 1.0,
                "via": "exacta",
            }

    vector_principal = get_or_embed_concepto(conn, concepto, embed_fn)
    resultados_principal = search_pictos(
        qdrant_client, collection, vector_principal, top=5, exclude_flagged=True
    )
    mejor_principal = resultados_principal[0] if resultados_principal else None

    if mejor_principal is not None and mejor_principal.score >= UMBRAL_SIMILITUD:
        candidatos = _candidatos_con_esquematicos(
            qdrant_client, collection, resultados_principal, vector_principal
        )
        return {
            "imagen_tipo": "picto",
            "picto_id": mejor_principal.id,
            "foto_path": None,
            "candidatos": candidatos,
            "concepto_ganador": concepto,
            "score_ganador": mejor_principal.score,
            "via": "principal",
        }

    resultados_por_termino: list[tuple[str, list]] = [(concepto, resultados_principal)]
    for candidato in candidatos_concepto:
        exactos_candidato = find_exact_match_in_index(indice, candidato)
        if exactos_candidato:
            candidatos = [{"id": i, "schematic": False} for i in exactos_candidato[:5]]
            return {
                "imagen_tipo": "picto",
                "picto_id": exactos_candidato[0],
                "foto_path": None,
                "candidatos": candidatos,
                "concepto_ganador": candidato,
                "score_ganador": 1.0,
                "via": "exacta",
            }
        vector_candidato = get_or_embed_concepto(conn, candidato, embed_fn)
        resultados_candidato = search_pictos(
            qdrant_client, collection, vector_candidato, top=5, exclude_flagged=True
        )
        resultados_por_termino.append((candidato, resultados_candidato))

    mejores_por_id: dict[int, object] = {}
    termino_por_id: dict[int, str] = {}
    for termino, resultados in resultados_por_termino:
        for r in resultados:
            actual = mejores_por_id.get(r.id)
            if actual is None or r.score > actual.score:
                mejores_por_id[r.id] = r
                termino_por_id[r.id] = termino

    top5_global = sorted(mejores_por_id.values(), key=lambda r: r.score, reverse=True)[:5]

    if top5_global and top5_global[0].score >= UMBRAL_SIMILITUD:
        ganador = top5_global[0]
        candidatos = _candidatos_con_esquematicos(
            qdrant_client, collection, top5_global, get_or_embed_concepto(conn, termino_por_id[ganador.id], embed_fn)
        )
        return {
            "imagen_tipo": "picto",
            "picto_id": ganador.id,
            "foto_path": None,
            "candidatos": candidatos,
            "concepto_ganador": termino_por_id[ganador.id],
            "score_ganador": ganador.score,
            "via": "candidato",
        }

    mejor_global = top5_global[0] if top5_global else None
    candidatos = [{"id": r.id, "schematic": False} for r in top5_global]
    return {
        "imagen_tipo": "picto",
        "picto_id": None,
        "foto_path": None,
        "candidatos": candidatos,
        "concepto_ganador": termino_por_id[mejor_global.id] if mejor_global else None,
        "score_ganador": mejor_global.score if mejor_global else None,
        "via": "sin_imagen",
    }


def _candidatos_con_esquematicos(qdrant_client, collection: str, resultados_limpios, vector: list[float]) -> list[dict]:
    candidatos = [{"id": r.id, "schematic": False} for r in resultados_limpios[:5]]
    ids_ya_presentes = {c["id"] for c in candidatos}
    resultados_todos = search_pictos(qdrant_client, collection, vector, top=10, exclude_flagged=False)
    esquematicos = [
        r for r in resultados_todos
        if r.payload.get("schematic")
        and not r.payload.get("sex")
        and not r.payload.get("violence")
        and r.id not in ids_ya_presentes
    ]
    for r in esquematicos[:MAX_ESQUEMATICOS]:
        candidatos.append({"id": r.id, "schematic": True})
    return candidatos
