import argparse

from lib.config import Settings
from lib.embeddings import embed_texts
from lib.qdrant_client import get_client, search_pictos


def search_picto(query: str, qdrant_client, collection: str, embed_fn, top: int = 5) -> list[dict]:
    vector = embed_fn([query])[0]
    results = search_pictos(qdrant_client, collection, vector, top=top)
    return [
        {
            "id": r.payload["id"],
            "keywords": [kw["keyword"] for kw in r.payload["keywords"]],
            "score": r.score,
        }
        for r in results
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca pictos ARASAAC por concepto")
    parser.add_argument("concepto")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    settings = Settings()
    qdrant = get_client(settings.qdrant_url)

    def embed_fn(texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, api_key=settings.openai_api_key)

    resultados = search_picto(args.concepto, qdrant, settings.qdrant_collection, embed_fn, top=args.top)
    for r in resultados:
        print(f"{r['id']:>6}  {r['score']:.3f}  {', '.join(r['keywords'])}")


if __name__ == "__main__":
    main()
