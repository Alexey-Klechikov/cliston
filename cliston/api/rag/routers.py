from api.rag.models import ExtractCharacterProfileResponse
from api.rag.operators import handle_extract_character_profile
from fastapi import APIRouter, status

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/extract_character_profile", status_code=status.HTTP_200_OK)
async def extract_character_profile(character_name: str) -> ExtractCharacterProfileResponse:
    return await handle_extract_character_profile(character_name)
