# Interview Explanation

## 30-Second Version

Personal AI Scheduling Assistant is an AI workflow automation app, not just a calendar chatbot. A user writes a natural-language plan, an LLM extracts structured task candidates, the backend validates and normalizes those candidates, an algorithmic scheduler creates the timeline, and the UI shows conflicts and suggestions before calendar sync. The important design choice is that the LLM only handles understanding; deterministic backend logic owns scheduling correctness.

## 5-10 Minute Technical Version

The system is split into six layers.

1. React dashboard: users enter natural language and review the generated timeline, conflicts, and AI suggestions.
2. FastAPI backend: exposes typed endpoints and coordinates the scheduling workflow.
3. AI task understanding: uses OpenAI structured extraction through `OPENAI_API_KEY`, retries once with a stricter prompt if the LLM merges tasks, and falls back to a local parser when needed.
4. Validation layer: checks missing durations, invalid fixed tasks, overlaps, and impossible time windows.
5. Scheduling engine: locks fixed tasks first, ranks flexible tasks by priority and duration, finds available windows, adds prep buffers, and emits conflict-resolution suggestions.
6. Calendar boundary: returns sync status today and is structured for Google Calendar OAuth event create/update/delete later.

The key architectural point is separation of concerns. LLM output is treated as an untrusted task candidate, then validated and scheduled by normal backend code. That prevents hallucinated times or malformed tasks from becoming calendar events without checks.

## Why It Is Strong

- Demonstrates LLM workflows without relying on the LLM for all logic.
- Shows backend engineering through validation, orchestration, typed schemas, and conflict handling.
- Has a recruiter-friendly demo: input text goes in, a schedule and conflicts come out.
- Leaves clear production extension points for auth, PostgreSQL, encrypted OAuth tokens, recurring tasks, notifications, and calendar sync retries.
