# Personal AI Scheduling Assistant

An AI-powered scheduling workflow system that turns natural language plans into structured tasks, validates constraints, detects conflicts, and generates a calendar-ready daily timeline.

This is intentionally more than a calendar chatbot: the LLM understands the request, but deterministic backend logic owns scheduling correctness.

![Architecture](docs/architecture.svg)

## Demo Workflow

Input:

```text
Tomorrow wake up at 6am, gym at 7am, office at 9am, interview at 12:30pm,
parents call for 20 mins, study 2 hours, sleep by 10:30pm.
```

System:

1. Extracts structured tasks from natural language.
2. Classifies fixed tasks versus flexible tasks.
3. Validates missing durations and overlapping time windows.
4. Locks fixed tasks first.
5. Adds prep buffers around high-priority events.
6. Places flexible tasks into open time slots.
7. Detects conflicts such as Office overlapping the Interview.
8. Returns a timeline, warnings, suggestions, and calendar sync status.

## Screenshots

Screenshots are stored in `docs/screenshots/`.

| Dashboard | Schedule Timeline |
| --- | --- |
| ![Dashboard](docs/screenshots/dashboard.png) | ![Timeline](docs/screenshots/timeline.png) |

| Conflict Detection | Suggestions Panel |
| --- | --- |
| ![Conflicts](docs/screenshots/conflict_detection.png) | ![Suggestions](docs/screenshots/suggestions_panel.png) |

## Features

- Natural language schedule input.
- OpenAI-compatible structured task extraction.
- Local fallback parser for demos without API keys.
- Task validation for missing durations, overlaps, and impossible fixed-time plans.
- Algorithmic scheduling engine for fixed and flexible tasks.
- Priority-based flexible task placement.
- Automatic prep buffers for high-priority events.
- Conflict and suggestion output.
- Calendar sync boundary for future Google Calendar OAuth.
- React dashboard with timeline and suggestions panel.

## Architecture

```text
React Dashboard
  -> FastAPI Backend
  -> AI Task Understanding Layer
  -> Task Validation Layer
  -> Scheduling and Optimization Engine
  -> Workflow Orchestration Layer
  -> Storage + Calendar Integration Boundary
```

The key design decision is separation of concerns:

- LLM: extracts intent into structured task candidates.
- Validator: treats extracted data as untrusted and checks it.
- Scheduler: deterministically allocates time blocks and detects conflicts.
- Orchestrator: manages lifecycle, persistence, and calendar sync boundaries.

## Project Structure

```text
personal-ai-scheduler/
  backend/     FastAPI, AI extraction, validation, scheduling, orchestration
  frontend/    React + Vite dashboard
  docs/        Architecture, screenshots, and interview notes
```

## Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Demo mode:

```text
http://localhost:5173/?demo=1
```

## API Example

```bash
curl -X POST http://127.0.0.1:8000/api/schedules/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Tomorrow gym at 7am, office at 9am, interview at 12:30pm, parents call for 20 mins, study 2 hours."}'
```

## Example Prompts

```text
Tomorrow gym at 7am, office at 9am, interview at 12:30pm, parents call for 20 mins.
```

```text
Plan tomorrow: wake up at 6am, deep work for 2 hours, team meeting at 11am, lunch, study 90 minutes, sleep by 10:30pm.
```

```text
Move gym to evening and keep all meetings after lunch.
```

## Recruiter Explanation

Short version:

> This is an AI workflow automation app for scheduling. The LLM extracts tasks from natural language, then the backend validates constraints and uses a deterministic scheduler to build a conflict-aware calendar timeline.

Deep technical version:

[docs/interview_explanation.md](docs/interview_explanation.md)

## Production Roadmap

- PostgreSQL storage with user accounts.
- JWT authentication.
- Google OAuth 2.0 token storage with encryption.
- Google Calendar event create/update/delete.
- Drag-and-drop rescheduling.
- Recurring task expansion.
- Email, SMS, and push reminders.
- Background sync retries and failure logging.
- Evaluation set for LLM extraction quality.

