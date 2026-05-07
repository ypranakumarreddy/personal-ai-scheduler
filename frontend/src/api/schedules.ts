import type { AssistantChatResponse, CalendarAuthStatus, CalendarSyncResponse, ScheduleResponse } from "../types/schedule";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function generateSchedule(text: string): Promise<ScheduleResponse> {
  const response = await fetch(`${API_BASE}/api/schedules/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });

  if (!response.ok) {
    throw new Error("Unable to generate schedule");
  }

  return response.json();
}

export async function sendAssistantMessage(message: string, sessionId = "default"): Promise<AssistantChatResponse> {
  const response = await fetch(`${API_BASE}/api/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId })
  });

  if (!response.ok) {
    throw new Error(await readError(response, "Assistant request failed"));
  }

  return response.json();
}

export async function getCalendarStatus(): Promise<CalendarAuthStatus> {
  const response = await fetch(`${API_BASE}/auth/google/status`);
  if (!response.ok) {
    throw new Error(await readError(response, "Unable to read calendar status"));
  }
  return response.json();
}

export function googleLoginUrl() {
  return `${API_BASE}/auth/google/login`;
}

export async function syncCalendar(sessionId = "default"): Promise<CalendarSyncResponse> {
  const response = await fetch(`${API_BASE}/calendar/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Calendar sync failed"));
  }
  return response.json();
}

async function readError(response: Response, fallback: string) {
  try {
    const body = await response.json();
    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}
