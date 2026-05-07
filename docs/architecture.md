# Architecture

![Architecture diagram](architecture.svg)

## Flow

```text
React Chatbot Assistant
  -> FastAPI Backend
  -> LLM Structured Extraction Layer
  -> Task Validation Layer
  -> Scheduling and Optimization Engine
  -> Workflow Orchestration Layer
  -> SQLite/PostgreSQL-ready Storage
  -> Calendar Integration Boundary
```

## Backend Modules

- `ai_extraction_service.py`: converts natural language into structured task candidates.
- `task_validation_service.py`: checks missing durations, invalid dates, overlaps, and impossible windows.
- `scheduling_engine.py`: locks fixed tasks, finds open slots, schedules flexible work, and emits suggestions.
- `workflow_orchestrator.py`: coordinates extraction, validation, scheduling, persistence, and calendar sync.
- `calendar_sync_service.py`: integration boundary for Google Calendar OAuth and event sync.

## Why LLM + Algorithm

The LLM is useful for language understanding, but the project does not trust the LLM to decide the final calendar. OpenAI extracts structured task candidates; those candidates move through validation, normalization, and deterministic scheduling before anything is considered calendar-ready.

This makes the system safer and easier to explain:

- Natural language ambiguity is handled by the AI task understanding layer.
- Correctness is handled by typed schemas, validation, and scheduling code.
- Calendar sync is isolated behind a service boundary for retries and OAuth handling.

## Production Roadmap

- Replace SQLite development storage with PostgreSQL.
- Add user accounts, JWT auth, and encrypted OAuth token storage.
- Enable Google Calendar OAuth 2.0 event create/update/delete.
- Add drag-and-drop rescheduling persistence.
- Add recurring task expansion.
- Add notification jobs with Celery or a managed queue.
- Add observability for AI extraction failures, schedule conflicts, and calendar sync retries.
