from uuid import uuid4
import logging

from app.core.config import get_settings
from app.schemas.schedule import ScheduleRequest, ScheduleResponse
from app.services.ai_extraction_service import AITaskUnderstandingService
from app.services.calendar_sync_service import CalendarSyncService
from app.services.fallback_parser import has_multiple_intents, parse_with_fallback
from app.services.scheduling_engine import SchedulingEngine
from app.services.storage_service import ScheduleStorageService
from app.services.task_validation_service import TaskValidationService

logger = logging.getLogger(__name__)


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
        if self._needs_extraction_repair(request.text, extraction):
            repaired = parse_with_fallback(request.text, request.target_date)
            repaired.warnings.append("Malformed extraction repaired before scheduling.")
            extraction = repaired
        logger.info(
            "extracted_tasks_before_scheduling",
            extra={
                "task_count": len(extraction.tasks),
                "tasks": [task.model_dump(mode="json") for task in extraction.tasks],
            },
        )
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

    def _needs_extraction_repair(self, text: str, extraction) -> bool:
        if has_multiple_intents(text) and len(extraction.tasks) <= 1:
            return True
        return any(len(task.title.split()) > 12 for task in extraction.tasks)
