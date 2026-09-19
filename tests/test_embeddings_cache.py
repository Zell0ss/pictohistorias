import backend.services.embeddings_cache as embeddings_cache_module


def test_get_or_embed_concepto_returns_cached_without_calling_embed_fn(monkeypatch):
    monkeypatch.setattr(
        embeddings_cache_module, "get_cached_embedding", lambda conn, normalizado: [0.9, 0.9]
    )

    def _embed_fn_should_not_be_called(texts):
        raise AssertionError("embed_fn no debería llamarse en un cache hit")

    resultado = embeddings_cache_module.get_or_embed_concepto(
        conn=object(), concepto="Coche", embed_fn=_embed_fn_should_not_be_called
    )

    assert resultado == [0.9, 0.9]


def test_get_or_embed_concepto_embeds_and_caches_on_miss(monkeypatch):
    monkeypatch.setattr(embeddings_cache_module, "get_cached_embedding", lambda conn, normalizado: None)

    set_calls = []
    monkeypatch.setattr(
        embeddings_cache_module, "set_cached_embedding",
        lambda conn, normalizado, embedding: set_calls.append((normalizado, embedding)),
    )

    def fake_embed_fn(texts):
        assert texts == ["Coche"]
        return [[0.1, 0.2]]

    resultado = embeddings_cache_module.get_or_embed_concepto(
        conn=object(), concepto="Coche", embed_fn=fake_embed_fn
    )

    assert resultado == [0.1, 0.2]
    assert set_calls == [("coche", [0.1, 0.2])]
