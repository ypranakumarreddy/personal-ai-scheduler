from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.schedule import ScheduleResponse


AssistantIntent = Literal[
    "create_schedule",
    "ask_question",
    "modify_schedule",
    "add_task",
    "remove_task",
    "optimize_schedule",
    "sync_calendar",
]


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = "default"
    timezone: str | None = None


class AssistantChatResponse(BaseModel):
    session_id: str
    intent: AssistantIntent
    assistant_message: str
    suggested_actions: list[str]
    schedule: ScheduleResponse | None = None
    calendar_authenticated: bool = False


class CalendarAuthStatus(BaseModel):
    authenticated: bool
    configured: bool
    message: str


class CalendarSyncRequest(BaseModel):
    session_id: str = "default"


class CalendarEventResult(BaseModel):
    title: str
    status: str
    event_link: str | None = None
    error: str | None = None


class CalendarSyncResponse(BaseModel):
    authenticated: bool
    configured: bool
    created_count: int
    failed_events: list[CalendarEventResult]
    event_links: list[str]
    message: str
