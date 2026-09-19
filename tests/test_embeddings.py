import lib.embeddings as embeddings_module


class FakeEmbeddingItem:
    def __init__(self, embedding):
        self.embedding = embedding


class FakeEmbeddingsResponse:
    def __init__(self, vectors):
        self.data = [FakeEmbeddingItem(v) for v in vectors]


class FakeEmbeddingsAPI:
    def __init__(self, vectors_by_call):
        self._vectors_by_call = vectors_by_call
        self.calls = []

    def create(self, model, input):
        self.calls.append({"model": model, "input": input})
        vectors = self._vectors_by_call[len(self.calls) - 1]
        return FakeEmbeddingsResponse(vectors)


class FakeOpenAIClient:
    def __init__(self, vectors_by_call, **kwargs):
        self.embeddings = FakeEmbeddingsAPI(vectors_by_call)


def test_embed_texts_batches_and_flattens(monkeypatch):
    vectors_by_call = [[[0.1, 0.2]], [[0.3, 0.4]]]
    fake_client = FakeOpenAIClient(vectors_by_call)
    monkeypatch.setattr(embeddings_module, "OpenAI", lambda api_key: fake_client)

    result = embeddings_module.embed_texts(["a", "b"], api_key="fake", batch_size=1)

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert len(fake_client.embeddings.calls) == 2
    assert fake_client.embeddings.calls[0]["input"] == ["a"]
    assert fake_client.embeddings.calls[1]["input"] == ["b"]


def test_embed_texts_uses_configured_model(monkeypatch):
    fake_client = FakeOpenAIClient([[[0.1, 0.2], [0.3, 0.4]]])
    monkeypatch.setattr(embeddings_module, "OpenAI", lambda api_key: fake_client)

    embeddings_module.embed_texts(["a", "b"], api_key="fake", batch_size=10)

    assert fake_client.embeddings.calls[0]["model"] == "text-embedding-3-small"
