from datetime import datetime, time, timedelta

from app.schemas.schedule import ExtractionResult, Priority, ScheduledBlock, TaskCandidate, TaskStatus, TaskType


class SchedulingEngine:
    def build_schedule(self, extraction: ExtractionResult) -> tuple[list[ScheduledBlock], list[str], list[str]]:
        day_start = datetime.combine(extraction.target_date, extraction.wake_time or time(6, 0))
        day_end = datetime.combine(extraction.target_date, extraction.sleep_time or time(22, 30))
        timeline: list[ScheduledBlock] = []
        conflicts: list[str] = []
        suggestions: list[str] = []

        fixed_tasks = [task for task in extraction.tasks if task.task_type == TaskType.fixed and task.start_time]
        flexible_tasks = [task for task in extraction.tasks if task not in fixed_tasks]

        for task in fixed_tasks:
            start = datetime.combine(extraction.target_date, task.start_time)
            end = start + timedelta(minutes=task.duration_minutes or 45)
            prep = self._prep_buffer_minutes(task)
            if prep:
                timeline.append(
                    ScheduledBlock(
                        task_id=task.id,
                        title=f"Prep for {task.title}",
                        start=start - timedelta(minutes=prep),
                        end=start,
                        block_type="buffer",
                        priority=task.priority,
                        notes="Automatic preparation buffer",
                    )
                )
            timeline.append(self._block(task, start, end))

        timeline.sort(key=lambda block: block.start)
        conflicts.extend(self._detect_block_conflicts(timeline))

        for task in self._rank_flexible_tasks(flexible_tasks):
            placed = self._place_flexible_task(task, timeline, day_start, day_end)
            if placed:
                timeline.append(placed)
                timeline.sort(key=lambda block: block.start)
            else:
                conflicts.append(f"No available slot for '{task.title}' ({task.duration_minutes or 45} minutes).")
                suggestions.append(f"Shorten '{task.title}' or move a fixed task to create room.")

        if day_end - day_start < timedelta(hours=7):
            suggestions.append("You have less than 7 hours between wake and sleep targets.")
        if self._has_back_to_back(timeline):
            suggestions.append("Some events are back-to-back. Add buffers if travel or context switching matters.")

        return timeline, conflicts, suggestions

    def _block(self, task: TaskCandidate, start: datetime, end: datetime) -> ScheduledBlock:
        return ScheduledBlock(
            task_id=task.id,
            title=task.title,
            start=start,
            end=end,
            priority=task.priority,
            status=TaskStatus.scheduled,
        )

    def _prep_buffer_minutes(self, task: TaskCandidate) -> int:
        title = task.title.lower()
        if task.priority == Priority.high or "interview" in title:
            return 15
        if "meeting" in title:
            return 10
        return 0

    def _rank_flexible_tasks(self, tasks: list[TaskCandidate]) -> list[TaskCandidate]:
        priority_weight = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
        return sorted(tasks, key=lambda task: (priority_weight[task.priority], -(task.duration_minutes or 0)))

    def _place_flexible_task(
        self,
        task: TaskCandidate,
        timeline: list[ScheduledBlock],
        day_start: datetime,
        day_end: datetime,
    ) -> ScheduledBlock | None:
        duration = timedelta(minutes=task.duration_minutes or 45)
        windows = self._available_windows(timeline, day_start, day_end)
        preferred_windows = self._prefer_windows(task, windows)

        for start, end in preferred_windows:
            if end - start >= duration:
                return self._block(task, start, start + duration)
        return None

    def _available_windows(
        self,
        timeline: list[ScheduledBlock],
        day_start: datetime,
        day_end: datetime,
    ) -> list[tuple[datetime, datetime]]:
        windows: list[tuple[datetime, datetime]] = []
        cursor = day_start
        for block in sorted(timeline, key=lambda item: item.start):
            if block.end <= day_start or block.start >= day_end:
                continue
            if block.start > cursor:
                windows.append((cursor, block.start))
            cursor = max(cursor, block.end)
        if cursor < day_end:
            windows.append((cursor, day_end))
        return windows

    def _prefer_windows(
        self,
        task: TaskCandidate,
        windows: list[tuple[datetime, datetime]],
    ) -> list[tuple[datetime, datetime]]:
        if "deep_work" in task.tags:
            return sorted(windows, key=lambda window: window[0].hour)
        if "meeting" in task.tags:
            return sorted(windows, key=lambda window: abs(window[0].hour - 14))
        if "energy" in task.tags:
            return sorted(windows, key=lambda window: abs(window[0].hour - 18))
        return windows

    def _detect_block_conflicts(self, timeline: list[ScheduledBlock]) -> list[str]:
        conflicts = []
        for current, nxt in zip(timeline, timeline[1:]):
            if current.end > nxt.start:
                conflicts.append(f"'{current.title}' conflicts with '{nxt.title}'.")
        return conflicts

    def _has_back_to_back(self, timeline: list[ScheduledBlock]) -> bool:
        for current, nxt in zip(timeline, sorted(timeline, key=lambda block: block.start)[1:]):
            if current.end == nxt.start and current.block_type == "task" and nxt.block_type == "task":
                return True
        return False

