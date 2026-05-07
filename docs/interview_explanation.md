# Interview Explanation

## 30-Second Version

Personal AI Scheduling Assistant is an AI workflow automation app, not just a calendar chatbot. A user chats with an assistant, LangGraph routes the message to the right backend tool, an LLM extracts structured task candidates when needed, the backend validates them, and an algorithmic scheduler creates the timeline before calendar sync. The important design choice is that the LLM handles understanding; deterministic backend logic owns scheduling correctness.

## 5-10 Minute Technical Version

The system is split into nine layers.

1. React dashboard: users enter natural language and review the generated timeline, conflicts, and AI suggestions.
2. FastAPI backend: exposes typed endpoints and coordinates the scheduling workflow.
3. LangGraph assistant orchestrator: loads memory, classifies intent, routes to tool nodes, and persists the result.
4. Intent detection: uses OpenAI when available and deterministic fallback rules when needed.
5. SQLite conversation memory: stores chat turns, latest schedule, extracted tasks, conflicts, warnings, and preferences for the active session.
6. AI task understanding: uses OpenAI structured extraction through `OPENAI_API_KEY`, retries once with a stricter prompt if the LLM merges tasks, and falls back to a local parser when needed.
7. Validation layer: checks missing durations, invalid fixed tasks, overlaps, and impossible time windows.
8. Scheduling engine: locks fixed tasks first, ranks flexible tasks by priority and duration, finds available windows, adds prep buffers, and emits conflict-resolution suggestions.
9. Calendar sync: supports Google OAuth routes and creates calendar events when credentials are configured.

The key architectural point is separation of concerns. LLM output is treated as an untrusted task candidate, then validated and scheduled by normal backend code. That prevents hallucinated times or malformed tasks from becoming calendar events without checks.

## Why It Is Strong

- Demonstrates LLM workflows without relying on the LLM for all logic.
- Shows backend engineering through validation, orchestration, typed schemas, and conflict handling.
- Has a recruiter-friendly demo: input text goes in, a schedule and conflicts come out.
- Leaves clear production extension points for auth, PostgreSQL, encrypted OAuth tokens, recurring tasks, notifications, and calendar sync retries.
