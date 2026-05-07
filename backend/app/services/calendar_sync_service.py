from app.core.config import get_settings
from app.schemas.schedule import ScheduledBlock


class CalendarSyncService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def sync(self, timeline: list[ScheduledBlock]) -> str:
        if not self.settings.enable_calendar_sync:
            return "skipped: calendar sync disabled"
        return f"queued: {len(timeline)} events ready for Google Calendar sync"

