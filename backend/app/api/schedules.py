from fastapi import APIRouter, HTTPException

from app.schemas.schedule import ScheduleRequest, ScheduleResponse
from app.services.workflow_orchestrator import ScheduleWorkflowOrchestrator

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
orchestrator = ScheduleWorkflowOrchestrator()


@router.post("/generate", response_model=ScheduleResponse)
async def generate_schedule(request: ScheduleRequest) -> ScheduleResponse:
    return await orchestrator.generate(request)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str) -> ScheduleResponse:
    schedule = orchestrator.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

