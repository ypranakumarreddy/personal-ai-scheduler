import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import TypedDict

from dateutil.parser import parse
from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse, AssistantIntent
from app.schemas.schedule import ScheduleRequest, ScheduleResponse, ScheduledBlock
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.workflow_orchestrator import ScheduleWorkflowOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class AssistantSessionState:
    session_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    latest_plan_text: str | None = None
    latest_schedule: ScheduleResponse | None = None
    user_preferences: dict[str, str] = field(default_factory=dict)


class AssistantGraphState(TypedDict, total=False):
    request: AssistantChatRequest
    message: str
    session: AssistantSessionState
    intent: AssistantIntent
    response: AssistantChatResponse


class AssistantConversationService:
    def __init__(
        self,
        orchestrator: ScheduleWorkflowOrchestrator | None = None,
        memory: ConversationMemoryService | None = None,
    ) -> None:
        self.orchestrator = orchestrator or ScheduleWorkflowOrchestrator()
        self.settings = get_settings()
        self.memory = memory or ConversationMemoryService()
        self.sessions: dict[str, AssistantSessionState] = {}
        self.graph = self._build_graph()

    async def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        result = await self.graph.ainvoke(
            {
                "request": request,
                "message": request.message.strip(),
            }
        )
        return result["response"]

    def get_state(self, session_id: str = "default") -> AssistantSessionState:
        return self._state(session_id)

    def has_schedule(self, session_id: str = "default") -> bool:
        return self._state(session_id).latest_schedule is not None

    def _state(self, session_id: str) -> AssistantSessionState:
        if session_id not in self.sessions:
            persisted = self.memory.load_session(session_id)
            turns = [
                ConversationTurn(role=turn["role"], content=turn["content"])
                for turn in self.memory.load_turns(session_id)
            ]
            self.sessions[session_id] = AssistantSessionState(
                session_id=session_id,
                turns=turns,
                latest_plan_text=persisted["latest_plan_text"] if persisted else None,
                latest_schedule=persisted["latest_schedule"] if persisted else None,
                user_preferences=persisted["user_preferences"] if persisted else {},
            )
        return self.sessions[session_id]

    def _build_graph(self):
        graph = StateGraph(AssistantGraphState)
        graph.add_node("load_memory", self._load_memory_node)
        graph.add_node("classify_intent", self._classify_intent_node)
        graph.add_node("create_schedule", self._create_schedule_node)
        graph.add_node("modify_schedule", self._modify_schedule_node)
        graph.add_node("answer_question", self._answer_question_node)
        graph.add_node("sync_calendar", self._sync_calendar_node)
        graph.add_node("persist_memory", self._persist_memory_node)

        graph.set_entry_point("load_memory")
        graph.add_edge("load_memory", "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self._route_intent,
            {
                "create_schedule": "create_schedule",
                "modify_schedule": "modify_schedule",
                "answer_question": "answer_question",
                "sync_calendar": "sync_calendar",
            },
        )
        graph.add_edge("create_schedule", "persist_memory")
        graph.add_edge("modify_schedule", "persist_memory")
        graph.add_edge("answer_question", "persist_memory")
        graph.add_edge("sync_calendar", "persist_memory")
        graph.add_edge("persist_memory", END)
        return graph.compile()

    async def _load_memory_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        request = graph_state["request"]
        session = self._state(request.session_id)
        message = graph_state["message"]
        session.turns.append(ConversationTurn(role="user", content=message))
        self.memory.append_turn(session.session_id, "user", message)
        return {"session": session}

    async def _classify_intent_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        session = graph_state["session"]
        message = graph_state["message"]
        intent = await self._detect_intent(message, session)
        logger.info("assistant_intent_detected", extra={"session_id": session.session_id, "intent": intent})
        return {"intent": intent}

    async def _create_schedule_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        request = graph_state["request"]
        response = await self._create_schedule(graph_state["session"], graph_state["message"], request.timezone)
        return {"response": response}

    async def _modify_schedule_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        request = graph_state["request"]
        response = await self._modify_schedule(
            graph_state["session"],
            graph_state["message"],
            graph_state["intent"],
            request.timezone,
        )
        return {"response": response}

    async def _answer_question_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        return {"response": self._answer_question(graph_state["session"], graph_state["message"])}

    async def _sync_calendar_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        session = graph_state["session"]
        response = self._simple_response(
            session,
            "sync_calendar",
            "I can sync the current timeline once Google Calendar is connected. Use the calendar button on the right to connect or sync.",
            ["Connect Google Calendar", "Sync to Calendar"],
        )
        return {"response": response}

    async def _persist_memory_node(self, graph_state: AssistantGraphState) -> AssistantGraphState:
        session = graph_state["session"]
        response = graph_state["response"]
        session.turns.append(ConversationTurn(role="assistant", content=response.assistant_message))
        self.memory.append_turn(session.session_id, "assistant", response.assistant_message)
        self.memory.save_session(
            session.session_id,
            session.latest_plan_text,
            session.latest_schedule,
            session.user_preferences,
        )
        return {}

    def _route_intent(self, graph_state: AssistantGraphState) -> str:
        intent = graph_state["intent"]
        if intent == "create_schedule":
            return "create_schedule"
        if intent == "sync_calendar":
            return "sync_calendar"
        if intent in {"modify_schedule", "add_task", "remove_task", "optimize_schedule"}:
            return "modify_schedule"
        return "answer_question"

    async def _detect_intent(self, message: str, state: AssistantSessionState) -> AssistantIntent:
        if self.settings.openai_api_key:
            try:
                return await self._detect_intent_with_openai(message, state)
            except Exception as exc:
                logger.warning("assistant_intent_llm_failed", extra={"error": str(exc)})
        return self._detect_intent_with_rules(message, state)

    async def _detect_intent_with_openai(self, message: str, state: AssistantSessionState) -> AssistantIntent:
        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the user's scheduling assistant intent. "
                        "Return JSON only. Valid intents are create_schedule, ask_question, "
                        "modify_schedule, add_task, remove_task, optimize_schedule, sync_calendar."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Has active schedule: {state.latest_schedule is not None}\n"
                        f"Recent turns: {[turn.content for turn in state.turns[-6:]]}\n"
                        f"Message: {message}\n"
                        'Return shape: {"intent":"create_schedule"}'
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        intent = data.get("intent")
        valid: set[AssistantIntent] = {
            "create_schedule",
            "ask_question",
            "modify_schedule",
            "add_task",
            "remove_task",
            "optimize_schedule",
            "sync_calendar",
        }
        if intent in valid:
            return intent
        return self._detect_intent_with_rules(message, state)

    def _detect_intent_with_rules(self, message: str, state: AssistantSessionState) -> AssistantIntent:
        lower = message.lower()
        if any(phrase in lower for phrase in ("sync", "calendar")):
            return "sync_calendar"
        if any(phrase in lower for phrase in ("remove", "delete", "drop", "cancel")):
            return "remove_task"
        if lower.startswith("add ") or " add " in f" {lower} ":
            return "add_task"
        if any(phrase in lower for phrase in ("move", "reschedule", "change", "shift")):
            return "modify_schedule"
        if any(phrase in lower for phrase in ("optimize", "make better", "fix my schedule")):
            return "optimize_schedule"
        if self._looks_like_new_plan(lower, state):
            return "create_schedule"
        return "ask_question"

    def _looks_like_new_plan(self, lower: str, state: AssistantSessionState) -> bool:
        plan_words = ("plan", "schedule", "tomorrow", "today")
        task_words = ("wake", "interview", "gym", "office", "study", "sleep", "walk", "meeting")
        if not state.latest_schedule:
            return any(word in lower for word in plan_words + task_words)
        return any(word in lower for word in plan_words) and any(word in lower for word in task_words)

    async def _create_schedule(
        self,
        state: AssistantSessionState,
        message: str,
        timezone: str | None,
    ) -> AssistantChatResponse:
        schedule = await self.orchestrator.generate(ScheduleRequest(text=message, timezone=timezone))
        state.latest_plan_text = message
        state.latest_schedule = schedule
        return AssistantChatResponse(
            session_id=state.session_id,
            intent="create_schedule",
            assistant_message=self._schedule_summary(schedule),
            suggested_actions=self._suggested_actions(schedule),
            schedule=schedule,
        )

    async def _modify_schedule(
        self,
        state: AssistantSessionState,
        message: str,
        intent: AssistantIntent,
        timezone: str | None,
    ) -> AssistantChatResponse:
        if not state.latest_plan_text:
            return self._simple_response(
                state,
                intent,
                "I can do that after we create a schedule. Send me your full day plan first.",
                ["Create a schedule", "Try the sample plan"],
            )

        updated_plan = self._rewrite_plan_text(state.latest_plan_text, message, intent)
        schedule = await self.orchestrator.generate(ScheduleRequest(text=updated_plan, timezone=timezone))
        state.latest_plan_text = updated_plan
        state.latest_schedule = schedule
        return AssistantChatResponse(
            session_id=state.session_id,
            intent=intent,
            assistant_message=f"I updated the schedule based on: {message}. {self._schedule_summary(schedule)}",
            suggested_actions=self._suggested_actions(schedule),
            schedule=schedule,
        )

    def _rewrite_plan_text(self, current_plan: str, message: str, intent: AssistantIntent) -> str:
        lower = message.lower()
        if intent == "remove_task":
            removable = ("gym", "walk", "parents", "study", "interview", "office", "dinner")
            for word in removable:
                if word in lower:
                    return f"{current_plan}. Remove {word} from the schedule."
        if intent == "modify_schedule":
            return f"{current_plan}. Update request: {message}."
        if intent == "optimize_schedule":
            return f"{current_plan}. Optimize the remaining flexible tasks and avoid back-to-back items."
        return f"{current_plan}. {message}."

    def _answer_question(self, state: AssistantSessionState, message: str) -> AssistantChatResponse:
        schedule = state.latest_schedule
        if not schedule:
            return self._simple_response(
                state,
                "ask_question",
                "I do not have a schedule in memory yet. Send me your day plan and I will build one first.",
                ["Create a schedule", "Use sample plan"],
            )

        lower = message.lower()
        if "after" in lower:
            answer = self._answer_after_time(schedule, message)
        elif "before bed" in lower or "free time" in lower:
            answer = self._answer_free_time(schedule)
        elif "pending" in lower or "tasks" in lower:
            answer = self._answer_pending(schedule)
        elif "fit" in lower or "study" in lower:
            answer = self._answer_fit_duration(schedule, message)
        elif "why" in lower:
            answer = self._answer_why(schedule, message)
        else:
            answer = f"Your current schedule has {len(self._task_blocks(schedule))} tasks. Ask me about free time, pending tasks, why something was placed, or ask me to add or move an item."

        return AssistantChatResponse(
            session_id=state.session_id,
            intent="ask_question",
            assistant_message=answer,
            suggested_actions=["Add a task", "Move a task", "Sync to Calendar"],
            schedule=schedule,
        )

    def _answer_after_time(self, schedule: ScheduleResponse, message: str) -> str:
        target = self._extract_time_from_text(message) or time(19, 20)
        blocks = [block for block in self._task_blocks(schedule) if block.start.time() >= target]
        if not blocks:
            return f"After {self._format_time(target)}, you do not have any scheduled tasks. That is open time before bed."
        items = ", ".join(f"{block.title} at {self._format_dt(block.start)}" for block in blocks)
        return f"After {self._format_time(target)}, you have: {items}."

    def _answer_free_time(self, schedule: ScheduleResponse) -> str:
        windows = self._free_windows(schedule)
        if not windows:
            return "I do not see meaningful free time in the current schedule."
        readable = ", ".join(f"{self._format_dt(start)}-{self._format_dt(end)}" for start, end in windows if end - start >= timedelta(minutes=30))
        return f"Yes. Your open windows are: {readable or 'shorter than 30 minutes each'}."

    def _answer_pending(self, schedule: ScheduleResponse) -> str:
        tasks = ", ".join(block.title for block in self._task_blocks(schedule))
        return f"Pending scheduled tasks are: {tasks}."

    def _answer_fit_duration(self, schedule: ScheduleResponse, message: str) -> str:
        duration = self._extract_duration(message) or 60
        for start, end in self._free_windows(schedule):
            if end - start >= timedelta(minutes=duration):
                return f"Yes. You can fit {duration} minutes from {self._format_dt(start)} to {self._format_dt(start + timedelta(minutes=duration))}."
        return f"I do not see an open {duration}-minute slot without moving something."

    def _answer_why(self, schedule: ScheduleResponse, message: str) -> str:
        lower = message.lower()
        for block in self._task_blocks(schedule):
            if any(word in block.title.lower() for word in lower.split()):
                return f"I placed {block.title} at {self._format_dt(block.start)} because that slot was open after fixed tasks and matched its time window or preference."
        return "I placed flexible tasks in open slots after locking fixed-time tasks first, then respecting time windows and deadlines."

    def _free_windows(self, schedule: ScheduleResponse) -> list[tuple[datetime, datetime]]:
        blocks = sorted(self._task_blocks(schedule), key=lambda block: block.start)
        if not blocks:
            return []
        windows: list[tuple[datetime, datetime]] = []
        cursor = blocks[0].end
        for block in blocks[1:]:
            if block.start > cursor:
                windows.append((cursor, block.start))
            cursor = max(cursor, block.end)
        return windows

    def _task_blocks(self, schedule: ScheduleResponse) -> list[ScheduledBlock]:
        return [block for block in schedule.timeline if block.block_type == "task"]

    def _schedule_summary(self, schedule: ScheduleResponse) -> str:
        tasks = self._task_blocks(schedule)
        names = ", ".join(task.title for task in tasks[:6])
        return (
            f"I found {len(schedule.extracted_tasks)} tasks and created a draft schedule. "
            f"The timeline includes {names}. "
            f"I found {len(schedule.conflicts)} conflicts and {len(schedule.validation_warnings)} warnings."
        )

    def _suggested_actions(self, schedule: ScheduleResponse) -> list[str]:
        actions = ["Ask about free time", "Add a task", "Approve schedule"]
        if schedule.conflicts:
            actions.insert(0, "Resolve conflicts")
        return actions

    def _simple_response(
        self,
        state: AssistantSessionState,
        intent: AssistantIntent,
        message: str,
        actions: list[str],
    ) -> AssistantChatResponse:
        return AssistantChatResponse(
            session_id=state.session_id,
            intent=intent,
            assistant_message=message,
            suggested_actions=actions,
            schedule=state.latest_schedule,
        )

    def _extract_time_from_text(self, message: str) -> time | None:
        try:
            parsed = parse(message, fuzzy=True)
            return parsed.time().replace(second=0, microsecond=0)
        except Exception:
            return None

    def _extract_duration(self, message: str) -> int | None:
        import re

        lower = message.lower()
        hour = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h)\b", lower)
        minute = re.search(r"(\d+)\s*(minute|minutes|min|mins)\b", lower)
        total = 0
        if hour:
            total += int(float(hour.group(1)) * 60)
        if minute:
            total += int(minute.group(1))
        return total or None

    def _format_dt(self, value: datetime) -> str:
        return value.strftime("%-I:%M %p")

    def _format_time(self, value: time) -> str:
        return value.strftime("%-I:%M %p")
