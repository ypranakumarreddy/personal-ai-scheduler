from datetime import datetime, timedelta

from app.schemas.schedule import ExtractionResult, TaskCandidate, TaskType


class TaskValidationService:
    def validate(self, extraction: ExtractionResult) -> tuple[list[str], list[str]]:
        warnings = list(extraction.warnings)
        conflicts: list[str] = []

        for task in extraction.tasks:
            if not task.duration_minutes or task.duration_minutes <= 0:
                task.duration_minutes = self._default_duration(task)
                warnings.append(f"Duration missing for '{task.title}', defaulted to {task.duration_minutes} minutes.")
            if task.task_type == TaskType.fixed and not task.start_time:
                warnings.append(f"Fixed task '{task.title}' is missing a start time.")
            if task.task_type == TaskType.deadline and not (task.start_time or task.end_time or task.latest_end):
                warnings.append(f"Deadline task '{task.title}' is missing a deadline time.")
            if bool(task.earliest_start) != bool(task.latest_end):
                warnings.append(f"Task '{task.title}' has an incomplete time window.")
            if task.earliest_start and task.latest_end and task.earliest_start >= task.latest_end:
                warnings.append(f"Task '{task.title}' has an invalid time window.")
            if len(task.title.split()) > 12:
                warnings.append(f"Task '{task.title}' looks malformed and may contain multiple merged tasks.")

        fixed_tasks = [
            task
            for task in extraction.tasks
            if task.task_type in (TaskType.fixed, TaskType.deadline) and self._effective_start_time(task)
        ]
        fixed_tasks.sort(key=lambda task: self._effective_start_time(task))
        for current, nxt in zip(fixed_tasks, fixed_tasks[1:]):
            if self._end(extraction, current) > self._start(extraction, nxt):
                conflicts.append(f"'{current.title}' overlaps with '{nxt.title}'.")

        return warnings, conflicts

    def _start(self, extraction: ExtractionResult, task: TaskCandidate) -> datetime:
        return datetime.combine(extraction.target_date, self._effective_start_time(task))

    def _end(self, extraction: ExtractionResult, task: TaskCandidate) -> datetime:
        return self._start(extraction, task) + timedelta(minutes=task.duration_minutes or 0)

    def _effective_start_time(self, task: TaskCandidate):
        return task.start_time or task.end_time or task.latest_end

    def _default_duration(self, task: TaskCandidate) -> int:
        lower = task.title.lower()
        if "wake" in lower or "sleep" in lower:
            return 15
        if "office" in lower:
            return 8 * 60
        if "gym" in lower or "workout" in lower:
            return 60
        if "walk" in lower:
            return 60
        if "interview" in lower or "meeting" in lower:
            return 60
        if "call" in lower:
            return 20
        return 45
