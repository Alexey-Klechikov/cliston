import logging

from api.rag.models import ExtractCharacterProfileResponse, LoadDocumentsResponse
from api.rag.prompts import CharacterPersonalityExtractionPrompt
from config import ModelConfig
from services.document.loader import get_document_loader
from services.genai.operators import ask
from services.vectors.retriever import HybridRetriever
from services.vectors.store import get_vector_store


async def _load_documents() -> LoadDocumentsResponse:
    logging.info("Loading documents (books)...")

    document_loader = get_document_loader()
    vector_store = get_vector_store()

    chunks = await document_loader.get_all_chunks()
    await vector_store.add_documents(chunks=chunks, skip_existing_chunks=True)

    verification = await vector_store.verify_storage()
    if verification.get("verified"):
        logging.info("Verification SUCCESS: All chunks properly stored with content and embeddings")
    else:
        logging.warning(f"Verification FAILED: {verification.get('message', 'Unknown issue')}")

    return LoadDocumentsResponse(status="success", chunks_loaded=len(chunks))


async def handle_extract_character_profile(character_name: str) -> ExtractCharacterProfileResponse:
    await _load_documents()

    logging.info("Extracting character profile...")

    vector_store = get_vector_store()
    retriever = HybridRetriever(vector_store)

    chunks = await retriever.retrieve(character_name)
    context = retriever.format_context(chunks)

    character_profile = await ask(
        model=ModelConfig.ASK_GEMINI_MODEL,
        system_prompt=CharacterPersonalityExtractionPrompt.get(),
        document_context=context,
        user_prompt="Character name to extract: " + character_name,
    )

    return ExtractCharacterProfileResponse(
        response=character_profile,
        character_name=character_name,
        sources=list({chunk.metadata.source for chunk in chunks if chunk.metadata and chunk.metadata.source}),
        num_context_chunks=len(chunks),
    )
