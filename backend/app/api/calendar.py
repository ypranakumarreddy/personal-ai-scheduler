from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.assistant import assistant_service
from app.api.schedules import orchestrator
from app.schemas.assistant import CalendarAuthStatus, CalendarSyncRequest, CalendarSyncResponse

router = APIRouter(tags=["calendar"])


@router.get("/auth/google/status", response_model=CalendarAuthStatus)
def google_status() -> CalendarAuthStatus:
    calendar = orchestrator.calendar
    if not calendar.configured():
        return CalendarAuthStatus(
            authenticated=False,
            configured=False,
            message="Google Calendar credentials are missing in backend/.env.",
        )
    return CalendarAuthStatus(
        authenticated=calendar.authenticated(),
        configured=True,
        message="Google Calendar connected." if calendar.authenticated() else "Google Calendar credentials configured but not connected.",
    )


@router.get("/auth/google/login")
def google_login():
    calendar = orchestrator.calendar
    if not calendar.configured():
        raise HTTPException(
            status_code=400,
            detail="Google credentials missing. Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI to backend/.env.",
        )
    return RedirectResponse(calendar.auth_url())


@router.get("/auth/google/callback")
def google_callback(code: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google authorization code.")
    orchestrator.calendar.exchange_code(code)
    return HTMLResponse(
        "<h2>Google Calendar connected</h2><p>You can close this tab and return to the scheduler.</p>"
    )


@router.post("/calendar/sync", response_model=CalendarSyncResponse)
def sync_calendar(request: CalendarSyncRequest) -> CalendarSyncResponse:
    state = assistant_service.get_state(request.session_id)
    if not state.latest_schedule:
        return CalendarSyncResponse(
            authenticated=orchestrator.calendar.authenticated(),
            configured=orchestrator.calendar.configured(),
            created_count=0,
            failed_events=[],
            event_links=[],
            message="No schedule is available to sync yet.",
        )
    return orchestrator.calendar.sync_blocks(state.latest_schedule.timeline)
