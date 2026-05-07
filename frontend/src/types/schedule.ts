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

export type AssistantIntent =
  | "create_schedule"
  | "ask_question"
  | "modify_schedule"
  | "add_task"
  | "remove_task"
  | "optimize_schedule"
  | "sync_calendar";

export interface AssistantChatResponse {
  session_id: string;
  intent: AssistantIntent;
  assistant_message: string;
  suggested_actions: string[];
  schedule: ScheduleResponse | null;
  calendar_authenticated: boolean;
}

export interface CalendarAuthStatus {
  authenticated: boolean;
  configured: boolean;
  message: string;
}

export interface CalendarSyncResponse {
  authenticated: boolean;
  configured: boolean;
  created_count: number;
  failed_events: Array<{
    title: string;
    status: string;
    event_link: string | null;
    error: string | null;
  }>;
  event_links: string[];
  message: string;
}
