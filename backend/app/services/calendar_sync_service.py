import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.assistant import CalendarEventResult, CalendarSyncResponse
from app.schemas.schedule import ScheduledBlock


class CalendarSyncService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    SCOPES = "https://www.googleapis.com/auth/calendar.events"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.tokens: dict[str, str | int] = {}

    def configured(self) -> bool:
        return bool(self.settings.google_client_id and self.settings.google_client_secret and self.settings.google_redirect_uri)

    def authenticated(self) -> bool:
        return bool(self.tokens.get("access_token"))

    def auth_url(self) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": self.SCOPES,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> None:
        payload = urlencode(
            {
                "code": code,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "redirect_uri": self.settings.google_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode()
        request = Request(self.TOKEN_URL, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode())
        self.tokens = data
        self.tokens["expires_at"] = int((datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))).timestamp())

    async def sync(self, timeline: list[ScheduledBlock]) -> str:
        if not self.configured():
            return "skipped: Google Calendar credentials missing"
        if not self.authenticated():
            return "skipped: Google Calendar not connected"
        return f"ready: {len([block for block in timeline if block.block_type == 'task'])} events can sync"

    def sync_blocks(self, timeline: list[ScheduledBlock]) -> CalendarSyncResponse:
        if not self.configured():
            return CalendarSyncResponse(
                authenticated=False,
                configured=False,
                created_count=0,
                failed_events=[],
                event_links=[],
                message="Google Calendar credentials are missing. Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI to backend/.env.",
            )
        if not self.authenticated():
            return CalendarSyncResponse(
                authenticated=False,
                configured=True,
                created_count=0,
                failed_events=[],
                event_links=[],
                message="Google Calendar is not connected. Use Connect Google Calendar first.",
            )

        created: list[str] = []
        failed: list[CalendarEventResult] = []
        for block in timeline:
            if block.block_type != "task":
                continue
            try:
                link = self._create_event(block)
                if link:
                    created.append(link)
            except Exception as exc:
                failed.append(CalendarEventResult(title=block.title, status="failed", error=str(exc)))

        return CalendarSyncResponse(
            authenticated=True,
            configured=True,
            created_count=len(created),
            failed_events=failed,
            event_links=created,
            message=f"Created {len(created)} Google Calendar events." if created else "No events were created.",
        )

    def _create_event(self, block: ScheduledBlock) -> str | None:
        body = {
            "summary": block.title,
            "description": block.notes or "Created by Personal AI Scheduling Assistant.",
            "start": {"dateTime": block.start.isoformat(), "timeZone": self.settings.default_timezone},
            "end": {"dateTime": block.end.isoformat(), "timeZone": self.settings.default_timezone},
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]},
        }
        request = Request(
            self.EVENTS_URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.tokens['access_token']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode())
        return data.get("htmlLink")
