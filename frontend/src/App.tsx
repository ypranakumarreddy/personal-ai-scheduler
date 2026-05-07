import {
  Bot,
  CalendarCheck,
  CheckCircle2,
  Clock3,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  Wand2
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { generateSchedule } from "./api/schedules";
import { SuggestionsPanel } from "./components/SuggestionsPanel";
import { Timeline } from "./components/Timeline";
import type { ScheduleResponse } from "./types/schedule";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  text: string;
};

const sample =
  "hey i want to wake up at 8am tomorrow morning i have a interview at 1pm i want to go to gym between 10am - 12pm i also want to talk with my parents atleast 20min i want to go to walk for 1hr at evening also main important i want to go to bed by 10:30pm";

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    text: "Hi, I am your scheduling assistant. Tell me what your day needs to include, and I will turn it into a conflict-aware calendar plan."
  },
  {
    id: "example",
    role: "assistant",
    text: "Try a messy request like: wake up at 8am, interview at 1pm, gym between 10am and 12pm, parents call for 20 minutes, walk for 1 hour in the evening, and bed by 10:30pm."
  }
];

export default function App() {
  const didRunDemo = useRef(false);
  const [input, setInput] = useState(sample);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<"draft" | "approved" | "synced">("draft");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!didRunDemo.current && new URLSearchParams(window.location.search).get("demo") === "1") {
      didRunDemo.current = true;
      void submitRequest(sample);
    }
  }, []);

  const scheduleStats = useMemo(() => {
    const taskCount = schedule?.timeline.filter((block) => block.block_type === "task").length ?? 0;
    const bufferCount = schedule?.timeline.filter((block) => block.block_type === "buffer").length ?? 0;
    return { taskCount, bufferCount };
  }, [schedule]);

  async function submitRequest(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setApprovalStatus("draft");
    setInput("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: trimmed },
      { id: crypto.randomUUID(), role: "assistant", text: "I am reading the request, extracting tasks, checking constraints, and building a timeline." }
    ]);

    try {
      const result = await generateSchedule(trimmed);
      setSchedule(result);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: buildAssistantSummary(result)
        }
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", text: `I could not generate the schedule yet. ${message}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitRequest(input);
  }

  function handleRegenerate() {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");
    void submitRequest(lastUserMessage?.text ?? sample);
  }

  function handleApprove() {
    if (schedule) {
      setApprovalStatus("approved");
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", text: "Schedule approved. I can now prepare this plan for calendar sync." }
      ]);
    }
  }

  function handleSync() {
    if (schedule) {
      setApprovalStatus("synced");
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "Calendar sync is queued in this MVP. The integration boundary is ready for Google Calendar OAuth."
        }
      ]);
    }
  }

  return (
    <main className="assistantShell">
      <section className="chatPanel">
        <header className="assistantHeader">
          <div className="brandMark">
            <Bot size={22} />
          </div>
          <div>
            <h1>AI Scheduling Assistant</h1>
            <p>Internal workflow assistant for planning, conflict detection, and calendar operations.</p>
          </div>
        </header>

        <div className="chatThread" aria-live="polite">
          {messages.map((message) => (
            <article className={`messageBubble ${message.role}`} key={message.id}>
              <div className="messageAvatar">{message.role === "assistant" ? <Sparkles size={16} /> : "You"}</div>
              <p>{message.text}</p>
            </article>
          ))}
          {isLoading && (
            <article className="messageBubble assistant">
              <div className="messageAvatar">
                <Loader2 className="spin" size={16} />
              </div>
              <p>Optimizing your day and checking for conflicts...</p>
            </article>
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="chatInput">Planning request</label>
          <textarea
            id="chatInput"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Plan my tomorrow with..."
          />
          <div className="composerActions">
            <button className="secondaryButton" type="button" onClick={() => setInput(sample)}>
              <RefreshCw size={16} />
              Sample
            </button>
            <button type="submit" disabled={isLoading}>
              {isLoading ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
              Generate Schedule
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="reviewPanel">
        <header className="reviewHeader">
          <div>
            <span className="eyebrow">Calendar Preview</span>
            <h2>{schedule ? `Schedule for ${schedule.target_date}` : "Draft Timeline"}</h2>
          </div>
          <StatusPill status={approvalStatus} />
        </header>

        <div className="metricsGrid">
          <Metric icon={<CalendarCheck size={17} />} label="Tasks" value={String(scheduleStats.taskCount)} />
          <Metric icon={<Clock3 size={17} />} label="Buffers" value={String(scheduleStats.bufferCount)} />
          <Metric
            icon={<Wand2 size={17} />}
            label="Issues"
            value={String(
              (schedule?.conflicts.length ?? 0) +
                (schedule?.suggestions.length ?? 0) +
                (schedule?.validation_warnings.length ?? 0)
            )}
          />
        </div>

        <Timeline blocks={schedule?.timeline ?? []} />

        <div className="workflowActions">
          <button type="button" disabled={!schedule || approvalStatus !== "draft"} onClick={handleApprove}>
            <CheckCircle2 size={16} />
            Approve Schedule
          </button>
          <button className="secondaryButton" type="button" onClick={handleRegenerate} disabled={isLoading}>
            <RefreshCw size={16} />
            Regenerate
          </button>
          <button type="button" disabled={!schedule || approvalStatus === "draft"} onClick={handleSync}>
            <CalendarCheck size={16} />
            Sync to Calendar
          </button>
        </div>

        <SuggestionsPanel
          conflicts={schedule?.conflicts ?? []}
          suggestions={schedule?.suggestions ?? []}
          warnings={schedule?.validation_warnings ?? []}
        />
      </section>
    </main>
  );
}

function buildAssistantSummary(schedule: ScheduleResponse) {
  const tasks = schedule.timeline.filter((block) => block.block_type === "task");
  const conflicts = schedule.conflicts.length;
  const warnings = schedule.validation_warnings.length;
  const extractedTitles = schedule.extracted_tasks.map((task) => task.title).slice(0, 6).join(", ");
  const firstTask = tasks[0]?.title ?? "your first task";
  const lastTask = tasks[tasks.length - 1]?.title ?? "your final task";

  return `I found ${schedule.extracted_tasks.length} tasks (${extractedTitles}) and created a draft schedule for ${schedule.target_date}. The timeline starts with ${firstTask} and ends with ${lastTask}. I found ${conflicts} conflict${conflicts === 1 ? "" : "s"} and ${warnings} validation warning${warnings === 1 ? "" : "s"} for review before calendar sync.`;
}

function StatusPill({ status }: { status: "draft" | "approved" | "synced" }) {
  return <span className={`statusPill ${status}`}>{status}</span>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="metricCard">
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
