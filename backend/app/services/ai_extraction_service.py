import json
from datetime import date

from app.core.config import get_settings
from app.schemas.schedule import ExtractionResult
from app.services.fallback_parser import parse_with_fallback


class AITaskUnderstandingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, text: str, target_date: date | None = None) -> ExtractionResult:
        if not self.settings.openai_api_key:
            return parse_with_fallback(text, target_date)

        try:
            return await self._extract_with_openai(text, target_date)
        except Exception as exc:
            fallback = parse_with_fallback(text, target_date)
            fallback.warnings.append(f"AI extraction failed; used fallback parser. Reason: {exc}")
            return fallback

    async def _extract_with_openai(self, text: str, target_date: date | None) -> ExtractionResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        prompt = {
            "role": "user",
            "content": (
                "Extract scheduling tasks from this request. Return only JSON matching this shape: "
                "{target_date: YYYY-MM-DD, wake_time: HH:MM|null, sleep_time: HH:MM|null, "
                "tasks: [{title, task_type: fixed|flexible|recurring|optional, start_time: HH:MM|null, "
                "duration_minutes, priority: high|medium|low, notes, depends_on: [], tags: []}], "
                "preferences: {}, warnings: []}. "
                f"Default date if ambiguous: {target_date.isoformat() if target_date else 'infer from text'}. "
                f"Request: {text}"
            ),
        }
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a strict JSON scheduling extraction engine."},
                prompt,
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        if target_date and not data.get("target_date"):
            data["target_date"] = target_date.isoformat()
        return ExtractionResult.model_validate(data)

