from pydantic import BaseModel


class LoadDocumentsResponse(BaseModel):
    status: str
    chunks_loaded: int


class ExtractCharacterProfileResponse(BaseModel):
    response: str
    character_name: str
    sources: list[str]
    num_context_chunks: int
