import json
from datetime import date, timedelta

from app.core.config import get_settings
from app.schemas.schedule import ExtractionResult
from app.services.fallback_parser import has_multiple_intents, parse_with_fallback


class AITaskUnderstandingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, text: str, target_date: date | None = None) -> ExtractionResult:
        if not self.settings.openai_api_key:
            fallback = parse_with_fallback(text, target_date)
            fallback.warnings.append("OPENAI_API_KEY is not configured; used fallback parser.")
            return fallback

        errors: list[str] = []
        for strict_retry in (False, True):
            try:
                extraction = await self._extract_with_openai(text, target_date, strict_retry)
                if self._looks_malformed(text, extraction):
                    errors.append("LLM extraction collapsed multiple intents into too few tasks.")
                    if not strict_retry:
                        continue
                    break
                return extraction
            except Exception as exc:
                errors.append(str(exc))
                if not strict_retry:
                    continue

        fallback = parse_with_fallback(text, target_date)
        fallback.warnings.append(f"LLM structured extraction failed; used fallback parser. Reason: {' | '.join(errors)}")
        return fallback

    async def _extract_with_openai(
        self,
        text: str,
        target_date: date | None,
        strict_retry: bool,
    ) -> ExtractionResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a production scheduling extraction service. "
                        "Your only job is to convert messy natural language into valid JSON task candidates. "
                        "Do not schedule the day. Do not merge multiple intents. "
                        "Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": self._prompt(text, target_date, strict_retry),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        normalized_date = target_date or self._infer_target_date(text)
        data["target_date"] = normalized_date.isoformat()
        for task in data.get("tasks", []):
            task["date"] = normalized_date.isoformat()
        return ExtractionResult.model_validate(data)

    def _prompt(self, text: str, target_date: date | None, strict_retry: bool) -> str:
        strict_note = ""
        if strict_retry:
            strict_note = (
                "STRICT RETRY: The previous extraction likely merged multiple tasks. "
                "Split every separate user intent into its own task object. "
            )

        return (
            f"{strict_note}"
            "Extract scheduling task candidates from the request. "
            "Return a JSON object with this exact shape:\n"
            "{\n"
            '  "target_date": "YYYY-MM-DD",\n'
            '  "wake_time": "HH:MM" | null,\n'
            '  "sleep_time": "HH:MM" | null,\n'
            '  "tasks": [\n'
            "    {\n"
            '      "title": "short normalized title",\n'
            '      "date": "YYYY-MM-DD" | null,\n'
            '      "start_time": "HH:MM" | null,\n'
            '      "end_time": "HH:MM" | null,\n'
            '      "earliest_start": "HH:MM" | null,\n'
            '      "latest_end": "HH:MM" | null,\n'
            '      "duration_minutes": number | null,\n'
            '      "task_type": "fixed" | "flexible" | "deadline" | "routine" | "optional",\n'
            '      "priority": "low" | "medium" | "high",\n'
            '      "constraints": ["specific constraint strings"],\n'
            '      "notes": "brief note" | null,\n'
            '      "confidence_score": number,\n'
            '      "depends_on": [],\n'
            '      "tags": []\n'
            "    }\n"
            "  ],\n"
            '  "preferences": {},\n'
            '  "warnings": []\n'
            "}\n\n"
            "Rules:\n"
            "- Split wake up, interview, gym, parents call, walk, and sleep into separate tasks.\n"
            "- Use fixed when an exact start time is mentioned.\n"
            "- Use flexible with earliest_start/latest_end for ranges like between 10am and 12pm.\n"
            "- Use deadline for phrases like sleep by 10:30pm.\n"
            "- Extract durations such as 20min or 1hr.\n"
            "- If duration is missing, leave duration_minutes null; backend will default it.\n"
            "- Set confidence_score from 0 to 1.\n"
            "- Do not invent calendar events beyond the user's intents.\n"
            f"- Default date if ambiguous: {target_date.isoformat() if target_date else 'infer today/tomorrow from text'}.\n\n"
            f"Request: {text}"
        )

    def _looks_malformed(self, text: str, extraction: ExtractionResult) -> bool:
        if has_multiple_intents(text) and len(extraction.tasks) <= 1:
            return True
        return any(len(task.title.split()) > 12 for task in extraction.tasks)

    def _infer_target_date(self, text: str) -> date:
        today = date.today()
        lower = text.lower()
        if "tomorrow" in lower:
            return today + timedelta(days=1)
        return today
