from datetime import datetime, timedelta

from app.schemas.schedule import ExtractionResult, TaskCandidate, TaskType


class TaskValidationService:
    def validate(self, extraction: ExtractionResult) -> tuple[list[str], list[str]]:
        warnings = list(extraction.warnings)
        conflicts: list[str] = []

        for task in extraction.tasks:
            if not task.duration_minutes or task.duration_minutes <= 0:
                warnings.append(f"Task '{task.title}' needs a positive duration.")
            if task.task_type == TaskType.fixed and not task.start_time:
                warnings.append(f"Fixed task '{task.title}' is missing a start time.")

        fixed_tasks = [task for task in extraction.tasks if task.task_type == TaskType.fixed and task.start_time]
        fixed_tasks.sort(key=lambda task: task.start_time)
        for current, nxt in zip(fixed_tasks, fixed_tasks[1:]):
            if self._end(extraction, current) > self._start(extraction, nxt):
                conflicts.append(f"'{current.title}' overlaps with '{nxt.title}'.")

        return warnings, conflicts

    def _start(self, extraction: ExtractionResult, task: TaskCandidate) -> datetime:
        return datetime.combine(extraction.target_date, task.start_time)

    def _end(self, extraction: ExtractionResult, task: TaskCandidate) -> datetime:
        return self._start(extraction, task) + timedelta(minutes=task.duration_minutes or 0)

