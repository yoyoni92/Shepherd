from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts, normalize_embeddings=True).tolist()


def get_chroma_ef():
    from chromadb import EmbeddingFunction, Documents, Embeddings

    class _EF(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            return embed(list(input))

    return _EF()
