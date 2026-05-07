from fastapi import APIRouter

from app.api.schedules import orchestrator
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import AssistantConversationService

router = APIRouter(prefix="/api/assistant", tags=["assistant"])
assistant_service = AssistantConversationService(orchestrator=orchestrator)


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(request: AssistantChatRequest) -> AssistantChatResponse:
    return await assistant_service.chat(request)
