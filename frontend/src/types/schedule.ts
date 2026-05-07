export type Priority = "high" | "medium" | "low";
export type TaskType = "fixed" | "flexible" | "recurring" | "optional";

export interface TaskCandidate {
  id: string;
  title: string;
  task_type: TaskType;
  start_time: string | null;
  duration_minutes: number | null;
  priority: Priority;
  status: string;
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

