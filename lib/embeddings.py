from openai import OpenAI


def embed_texts(
    texts: list[str],
    api_key: str,
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
) -> list[list[float]]:
    client = OpenAI(api_key=api_key)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors
