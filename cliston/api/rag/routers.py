from fastapi import APIRouter, status

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/extract_personality", status_code=status.HTTP_200_OK)
async def extract_personality(character_name: str) -> None:
    pass
