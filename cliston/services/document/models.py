from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    source: str
    chunk_index: int


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata

    id: str | None = None
    distance: float = 0.0
    keyword_score: float = 0.0


class Document(BaseModel):
    name: str
    file_path: str
    raw_text: str
    chunks: list[Chunk]
