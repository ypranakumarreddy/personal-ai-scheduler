import re
from dataclasses import dataclass
from datetime import date, time, timedelta

from dateutil.parser import parse

from app.schemas.schedule import ExtractionResult, Priority, TaskCandidate, TaskType


HIGH_PRIORITY_KEYWORDS = ("interview", "exam", "doctor", "deadline")
FIXED_TITLES = ("wake up", "sleep", "office", "interview", "meeting", "appointment")


@dataclass(frozen=True)
class IntentMatch:
    start: int
    end: int
    title: str


TASK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bwake(?:\s+up)?\b", "Wake Up"),
    (r"\binterview\b", "Interview"),
    (r"\boffice\b", "Office"),
    (r"\b(?:gym|workout|gy)\b", "Gym"),
    (r"\b(?:parents?\s+call|call\s+(?:my\s+)?parents?|talk\s+(?:to|with)\s+(?:my\s+)?parents?)\b", "Parents Call"),
    (r"\b(?:go\s+for\s+a\s+walk|walk)\b", "Walk"),
    (r"\b(?:study|deep\s+work)\b", "Study"),
    (r"\b(?:meeting|appointment)\b", "Meeting"),
    (r"\blunch\b", "Lunch"),
    (r"\bdinner\b", "Dinner"),
    (r"\b(?:sleep|bed|go\s+to\s+bed)\b", "Sleep"),
)


def parse_with_fallback(text: str, target_date: date | None = None) -> ExtractionResult:
    lowered = text.lower()
    selected_date = target_date or _infer_date(lowered)
    chunks = _extract_task_chunks(text)
    tasks: list[TaskCandidate] = []
    wake_time = None
    sleep_time = None
    warnings: list[str] = []

    for title_hint, chunk in chunks:
        clean = _clean_chunk(chunk)
        if not clean:
            continue

        title = title_hint or _title_from_chunk(clean)
        time_range = _extract_time_range(clean)
        start_time = _extract_time(clean)
        duration = _extract_duration(clean) or _default_duration(title)
        priority = Priority.high if any(word in clean.lower() for word in HIGH_PRIORITY_KEYWORDS) else Priority.medium
        notes: list[str] = []

        if not _extract_duration(clean) and title not in ("Wake Up", "Sleep"):
            warnings.append(f"Duration missing for '{title}', defaulted to {duration} minutes.")

        task_type = _task_type_for(title, clean, start_time, time_range)
        earliest_start = None
        latest_end = None

        if not time_range and not start_time:
            time_range = _implicit_time_range(title, clean)

        if time_range:
            earliest_start, latest_end = time_range
            start_time = None
            notes.append(f"Requested between {earliest_start.strftime('%H:%M')} and {latest_end.strftime('%H:%M')}.")

        if title == "Wake Up" and start_time:
            wake_time = start_time
        if title == "Sleep" and start_time:
            sleep_time = start_time

        tasks.append(
            TaskCandidate(
                title=title,
                date=selected_date,
                task_type=task_type,
                start_time=start_time,
                end_time=_end_time(start_time, duration),
                earliest_start=earliest_start,
                latest_end=latest_end,
                duration_minutes=duration,
                priority=priority,
                constraints=notes.copy(),
                notes=" ".join(notes) or None,
                confidence_score=0.72,
                tags=_tags_for(title),
            )
        )

    if has_multiple_intents(text) and len(tasks) <= 1:
        warnings.append("Multiple intents were detected, but extraction produced too few tasks.")

    return ExtractionResult(
        target_date=selected_date,
        wake_time=wake_time,
        sleep_time=sleep_time,
        tasks=tasks,
        preferences={"avoid_back_to_back": True},
        warnings=warnings,
    )


def has_multiple_intents(text: str) -> bool:
    return len(_find_intent_matches(text)) >= 2


def _infer_date(text: str) -> date:
    today = date.today()
    if "tomorrow" in text:
        return today + timedelta(days=1)
    return today


def _extract_task_chunks(text: str) -> list[tuple[str | None, str]]:
    matches = _find_intent_matches(text)
    if not matches:
        return [(None, part) for part in _split_on_separators(text)]

    chunks: list[tuple[str | None, str]] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start if index + 1 < len(matches) else len(text)
        chunk = text[match.start:next_start]
        chunks.append((match.title, chunk))

    prefix = text[: matches[0].start].strip(" ,.;:-")
    if prefix and not _looks_like_context_only(prefix):
        chunks.insert(0, (None, prefix))
    return chunks


def _find_intent_matches(text: str) -> list[IntentMatch]:
    matches: list[IntentMatch] = []
    occupied: list[range] = []

    for pattern, title in TASK_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            span_range = range(match.start(), match.end())
            if any(_ranges_overlap(span_range, existing) for existing in occupied):
                continue
            matches.append(IntentMatch(match.start(), match.end(), title))
            occupied.append(span_range)

    return sorted(matches, key=lambda item: item.start)


def _ranges_overlap(left: range, right: range) -> bool:
    return left.start < right.stop and right.start < left.stop


def _split_on_separators(text: str) -> list[str]:
    normalized = re.sub(r"\s+(?:and then|then|also)\s+", ",", text, flags=re.IGNORECASE)
    normalized = normalized.replace("\n", ",")
    return [part for part in re.split(r",|;|\n|- ", normalized) if part.strip()]


def _looks_like_context_only(text: str) -> bool:
    lower = text.lower()
    context_words = ("tomorrow", "today", "plan", "schedule", "my day", "my", "i want", "i have", "hey", "want", "to", "i")
    without_context = lower
    for word in context_words:
        without_context = without_context.replace(word, "")
    return not re.search(r"[a-z]", without_context)


def _clean_chunk(chunk: str) -> str:
    clean = chunk.strip(" .,:;-")
    clean = re.sub(r"^(tomorrow|today)\s*:?", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"^(and|then|also|i\s+also\s+want\s+to|i\s+want\s+to|i\s+have|i\s+need\s+to)\s+", "", clean, flags=re.IGNORECASE)
    return clean.strip(" .,:;-")


def _extract_time(chunk: str) -> time | None:
    lower = chunk.lower()
    if not any(marker in lower for marker in (" at ", " by ", "wake", "sleep", "interview", "meeting", "office")):
        return None

    exact_match = re.search(r"\b(?:at|by)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", chunk, re.IGNORECASE)
    matches = [exact_match] if exact_match else list(re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", chunk, re.IGNORECASE))

    for match in matches:
        if not match:
            continue
        suffix = chunk[match.end() : match.end() + 8].lower()
        if re.match(r"\s*(h|hr|hrs|hour|hours|min|mins|minute|minutes)\b", suffix):
            continue
        if not match.group(3) and not any(word in lower for word in ("wake", "sleep", "bed")):
            continue
        return _parse_time_parts(match.group(1), match.group(2), match.group(3))
    return None


def _extract_time_range(chunk: str) -> tuple[time, time] | None:
    match = re.search(
        r"\b(?:between|from)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:-|to|and)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        chunk,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    start_hour, start_minute, start_meridiem, end_hour, end_minute, end_meridiem = match.groups()
    if not start_meridiem and end_meridiem:
        start_meridiem = _infer_start_meridiem(int(start_hour), int(end_hour), end_meridiem)
    if start_meridiem and not end_meridiem:
        end_meridiem = start_meridiem

    return (
        _parse_time_parts(start_hour, start_minute, start_meridiem),
        _parse_time_parts(end_hour, end_minute, end_meridiem),
    )


def _implicit_time_range(title: str, chunk: str) -> tuple[time, time] | None:
    lower = chunk.lower()
    if "morning" in lower:
        return time(8, 0), time(12, 0)
    if "afternoon" in lower:
        return time(12, 0), time(17, 0)
    if "evening" in lower:
        return time(17, 0), time(21, 0)
    if title == "Parents Call":
        return time(19, 0), time(21, 30)
    return None


def _infer_start_meridiem(start_hour: int, end_hour: int, end_meridiem: str) -> str:
    if end_meridiem.lower() == "pm" and start_hour < end_hour:
        return "pm"
    if end_meridiem.lower() == "pm" and start_hour >= 8 and end_hour <= 12:
        return "am"
    return end_meridiem


def _parse_time_parts(hour: str, minute: str | None, meridiem: str | None) -> time:
    parsed = parse(f"{hour}:{int(minute or 0):02d} {meridiem or ''}")
    return parsed.time().replace(second=0, microsecond=0)


def _extract_duration(chunk: str) -> int | None:
    lower = chunk.lower()
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr)\b", lower)
    compact_hour_match = re.search(r"(\d+(?:\.\d+)?)\s*h\b", lower)
    minute_match = re.search(r"(\d+)\s*(minutes|minute|mins|min)\b", lower)
    compact_minute_match = re.search(r"(\d+)(minutes|minute|mins|min)\b", lower)
    total = 0
    if hour_match:
        total += int(float(hour_match.group(1)) * 60)
    elif compact_hour_match:
        total += int(float(compact_hour_match.group(1)) * 60)
    if minute_match:
        total += int(minute_match.group(1))
    elif compact_minute_match:
        total += int(compact_minute_match.group(1))
    return total or None


def _task_type_for(
    title: str,
    chunk: str,
    start_time: time | None,
    time_range: tuple[time, time] | None,
) -> TaskType:
    lower = chunk.lower()
    if any(word in lower for word in ("daily", "weekly", "every day", "every week")):
        return TaskType.routine
    if time_range:
        return TaskType.flexible
    if " by " in f" {lower} " and title == "Sleep":
        return TaskType.deadline
    if start_time and (title.lower() in FIXED_TITLES or any(marker in lower for marker in (" at ", " by "))):
        return TaskType.fixed
    return TaskType.flexible


def _end_time(start_time: time | None, duration_minutes: int | None) -> time | None:
    if not start_time or not duration_minutes:
        return None
    parsed = parse(f"{start_time.hour}:{start_time.minute:02d}") + timedelta(minutes=duration_minutes)
    return parsed.time().replace(second=0, microsecond=0)


def _title_from_chunk(chunk: str) -> str:
    cleaned = re.sub(r"\b(at|by|between|from|for)\b.*", "", chunk, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*(hours|hour|hrs|hr|h|minutes|minute|mins|min)\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(tomorrow|today|plan\s+my\s+tomorrow)\s*:?", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned.title() or chunk.strip().title()


def _default_duration(title: str) -> int:
    lower = title.lower()
    if lower == "wake up" or lower == "sleep":
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
    if "lunch" in lower or "dinner" in lower:
        return 45
    return 45


def _tags_for(title: str) -> list[str]:
    lower = title.lower()
    tags = []
    if any(word in lower for word in ("study", "deep work", "write", "code")):
        tags.append("deep_work")
    if any(word in lower for word in ("gym", "workout", "run", "walk")):
        tags.append("energy")
    if any(word in lower for word in ("interview", "meeting", "call")):
        tags.append("meeting")
    return tags
