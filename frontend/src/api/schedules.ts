import type { ScheduleResponse } from "../types/schedule";

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

