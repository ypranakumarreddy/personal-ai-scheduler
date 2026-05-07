from uuid import uuid4

from app.core.config import get_settings
from app.schemas.schedule import ScheduleRequest, ScheduleResponse
from app.services.ai_extraction_service import AITaskUnderstandingService
from app.services.calendar_sync_service import CalendarSyncService
from app.services.scheduling_engine import SchedulingEngine
from app.services.storage_service import ScheduleStorageService
from app.services.task_validation_service import TaskValidationService


class ScheduleWorkflowOrchestrator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.ai = AITaskUnderstandingService()
        self.validator = TaskValidationService()
        self.scheduler = SchedulingEngine()
        self.calendar = CalendarSyncService()
        self.storage = ScheduleStorageService()

    async def generate(self, request: ScheduleRequest) -> ScheduleResponse:
        timezone = request.timezone or self.settings.default_timezone
        extraction = await self.ai.extract(request.text, request.target_date)
        warnings, validation_conflicts = self.validator.validate(extraction)
        timeline, scheduling_conflicts, suggestions = self.scheduler.build_schedule(extraction)
        sync_status = await self.calendar.sync(timeline)

        response = ScheduleResponse(
            schedule_id=str(uuid4()),
            target_date=extraction.target_date,
            timezone=timezone,
            extracted_tasks=extraction.tasks,
            timeline=timeline,
            conflicts=validation_conflicts + scheduling_conflicts,
            suggestions=suggestions,
            validation_warnings=warnings,
            calendar_sync_status=sync_status,
        )
        self.storage.save(response)
        return response

    def get_schedule(self, schedule_id: str) -> ScheduleResponse | None:
        return self.storage.get(schedule_id)

