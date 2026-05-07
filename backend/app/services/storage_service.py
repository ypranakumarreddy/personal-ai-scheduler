import json
from pathlib import Path

from app.schemas.schedule import ScheduleResponse


class ScheduleStorageService:
    def __init__(self, path: str = "schedule_store.json") -> None:
        self.path = Path(path)

    def save(self, schedule: ScheduleResponse) -> None:
        data = self._load()
        data[schedule.schedule_id] = schedule.model_dump(mode="json")
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, schedule_id: str) -> ScheduleResponse | None:
        data = self._load().get(schedule_id)
        if not data:
            return None
        return ScheduleResponse.model_validate(data)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

