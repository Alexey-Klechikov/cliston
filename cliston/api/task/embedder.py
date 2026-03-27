from chromadb.api.types import Documents, Embeddings
from chromadb.utils.embedding_functions import EmbeddingFunction
from crewai.rag.embeddings.providers.custom.embedding_callable import CustomEmbeddingFunction
from services.embedder.client import get_embedding_service


class CustomEmbedder(EmbeddingFunction, CustomEmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embedder_service = get_embedding_service()

        results = embedder_service.embed_texts(input)

        return [r.tolist() for r in results]
