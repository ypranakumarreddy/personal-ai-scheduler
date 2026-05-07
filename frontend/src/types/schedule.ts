export type Priority = "high" | "medium" | "low";
export type TaskType = "fixed" | "flexible" | "deadline" | "routine" | "optional";

export interface TaskCandidate {
  id: string;
  title: string;
  date: string | null;
  task_type: TaskType;
  start_time: string | null;
  end_time: string | null;
  earliest_start: string | null;
  latest_end: string | null;
  duration_minutes: number | null;
  priority: Priority;
  status: string;
  constraints: string[];
  notes: string | null;
  confidence_score: number;
  tags: string[];
}

export interface ScheduledBlock {
  id: string;
  task_id: string | null;
  title: string;
  start: string;
  end: string;
  block_type: string;
  priority: Priority;
  status: string;
  notes: string | null;
}

export interface ScheduleResponse {
  schedule_id: string;
  target_date: string;
  timezone: string;
  extracted_tasks: TaskCandidate[];
  timeline: ScheduledBlock[];
  conflicts: string[];
  suggestions: string[];
  validation_warnings: string[];
  calendar_sync_status: string;
}
