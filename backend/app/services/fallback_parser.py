import re
from datetime import date, timedelta

from dateutil.parser import parse

from app.schemas.schedule import ExtractionResult, Priority, TaskCandidate, TaskType


FIXED_KEYWORDS = (" at ", " by ", "wake", "sleep", "office", "interview", "meeting")
HIGH_PRIORITY_KEYWORDS = ("interview", "exam", "doctor", "deadline")


def parse_with_fallback(text: str, target_date: date | None = None) -> ExtractionResult:
    lowered = text.lower()
    selected_date = target_date or _infer_date(lowered)
    chunks = _split_tasks(text)
    tasks: list[TaskCandidate] = []
    wake_time = None
    sleep_time = None
    warnings: list[str] = []

    for chunk in chunks:
        clean = chunk.strip(" .:-")
        if not clean:
            continue

        title = _title_from_chunk(clean)
        start_time = _extract_time(clean)
        duration = _extract_duration(clean)
        task_type = TaskType.fixed if start_time and _looks_fixed(clean) else TaskType.flexible
        priority = Priority.high if any(word in clean.lower() for word in HIGH_PRIORITY_KEYWORDS) else Priority.medium

        if "wake" in clean.lower() and start_time:
            wake_time = start_time
            continue
        if "sleep" in clean.lower() and start_time:
            sleep_time = start_time
            continue

        if duration is None:
            duration = _default_duration(title)
            warnings.append(f"Duration missing for '{title}', defaulted to {duration} minutes.")

        tasks.append(
            TaskCandidate(
                title=title,
                task_type=task_type,
                start_time=start_time,
                duration_minutes=duration,
                priority=priority,
                tags=_tags_for(title),
            )
        )

    return ExtractionResult(
        target_date=selected_date,
        wake_time=wake_time,
        sleep_time=sleep_time,
        tasks=tasks,
        preferences={"avoid_back_to_back": True},
        warnings=warnings,
    )


def _infer_date(text: str) -> date:
    today = date.today()
    if "tomorrow" in text:
        return today + timedelta(days=1)
    return today


def _split_tasks(text: str) -> list[str]:
    normalized = text.replace("\n", ",")
    return [part for part in re.split(r",|;|\n|- ", normalized) if part.strip()]


def _extract_time(chunk: str):
    lower = chunk.lower()
    if not any(marker in lower for marker in (" at ", " by ", "wake", "sleep")):
        return None
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", chunk, re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if meridiem:
        parsed = parse(f"{hour}:{minute:02d} {meridiem}")
        return parsed.time().replace(second=0, microsecond=0)
    return parse(f"{hour}:{minute:02d}").time().replace(second=0, microsecond=0)


def _extract_duration(chunk: str) -> int | None:
    lower = chunk.lower()
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr)\b", lower)
    minute_match = re.search(r"(\d+)\s*(minutes|minute|mins|min)\b", lower)
    total = 0
    if hour_match:
        total += int(float(hour_match.group(1)) * 60)
    if minute_match:
        total += int(minute_match.group(1))
    return total or None


def _looks_fixed(chunk: str) -> bool:
    lower = f" {chunk.lower()} "
    return any(keyword in lower for keyword in FIXED_KEYWORDS)


def _title_from_chunk(chunk: str) -> str:
    cleaned = re.sub(r"\b(at|by|for)\b.*", "", chunk, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*(hours|hour|hrs|hr|minutes|minute|mins|min)\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(tomorrow|today)\s*:?", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned.title() or chunk.strip().title()


def _default_duration(title: str) -> int:
    lower = title.lower()
    if "office" in lower:
        return 8 * 60
    if "gym" in lower or "workout" in lower:
        return 60
    if "interview" in lower or "meeting" in lower:
        return 60
    if "call" in lower:
        return 20
    return 45


def _tags_for(title: str) -> list[str]:
    lower = title.lower()
    tags = []
    if any(word in lower for word in ("study", "deep work", "write", "code")):
        tags.append("deep_work")
    if any(word in lower for word in ("gym", "workout", "run")):
        tags.append("energy")
    if any(word in lower for word in ("interview", "meeting", "call")):
        tags.append("meeting")
    return tags
