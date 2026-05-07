from datetime import date, datetime, time
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    fixed = "fixed"
    flexible = "flexible"
    recurring = "recurring"
    optional = "optional"


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"
    conflict = "conflict"
    completed = "completed"


class ScheduleRequest(BaseModel):
    text: str = Field(min_length=3)
    timezone: str | None = None
    target_date: date | None = None


class TaskCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    task_type: TaskType = TaskType.flexible
    start_time: time | None = None
    duration_minutes: int | None = None
    priority: Priority = Priority.medium
    status: TaskStatus = TaskStatus.pending
    notes: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    target_date: date
    wake_time: time | None = None
    sleep_time: time | None = None
    tasks: list[TaskCandidate]
    preferences: dict[str, str | int | bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ScheduledBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str | None = None
    title: str
    start: datetime
    end: datetime
    block_type: str = "task"
    priority: Priority = Priority.medium
    status: TaskStatus = TaskStatus.scheduled
    source: str = "scheduler"
    notes: str | None = None


class ScheduleResponse(BaseModel):
    schedule_id: str
    target_date: date
    timezone: str
    extracted_tasks: list[TaskCandidate]
    timeline: list[ScheduledBlock]
    conflicts: list[str]
    suggestions: list[str]
    validation_warnings: list[str]
    calendar_sync_status: str


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    task_type: TaskType | None = None
    priority: Priority | None = None

