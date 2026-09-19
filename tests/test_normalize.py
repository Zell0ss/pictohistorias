from lib.normalize import formas_singulares, normalize_concepto


def test_normalize_concepto_lowercases_and_strips_accents():
    assert normalize_concepto("Coche de Mamá") == "coche de mama"


def test_normalize_concepto_strips_whitespace():
    assert normalize_concepto("  José  ") == "jose"


def test_normalize_concepto_handles_enye():
    assert normalize_concepto("NIÑO") == "nino"


def test_normalize_concepto_idempotent_on_already_normalized():
    assert normalize_concepto("coche") == "coche"


def test_formas_singulares_strips_trailing_es():
    assert formas_singulares("autobuses") == ["autobuses", "autobuse", "autobus"]


def test_formas_singulares_strips_trailing_s():
    assert formas_singulares("coches") == ["coches", "coche", "coch"]


def test_formas_singulares_leaves_short_or_non_plural_words_alone():
    assert formas_singulares("coche") == ["coche"]
    assert formas_singulares("mas") == ["mas"]  # len 3, too short to strip
