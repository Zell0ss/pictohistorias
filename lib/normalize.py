import unicodedata


def normalize_concepto(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.lower().strip()


def formas_singulares(normalizado: str) -> list[str]:
    formas = [normalizado]
    if len(normalizado) > 3 and normalizado.endswith("s"):
        formas.append(normalizado[:-1])
    if len(normalizado) > 4 and normalizado.endswith("es"):
        sin_es = normalizado[:-2]
        if sin_es not in formas:
            formas.append(sin_es)
    return formas
