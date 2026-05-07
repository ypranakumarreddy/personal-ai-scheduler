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

import { getCalendarStatus, googleLoginUrl, sendAssistantMessage, syncCalendar } from "./api/schedules";
import { SuggestionsPanel } from "./components/SuggestionsPanel";
import { Timeline } from "./components/Timeline";
import type { CalendarAuthStatus, ScheduleResponse } from "./types/schedule";

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
  const [isSyncing, setIsSyncing] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<"draft" | "approved" | "synced">("draft");
  const [calendarStatus, setCalendarStatus] = useState<CalendarAuthStatus | null>(null);
  const [suggestedActions, setSuggestedActions] = useState<string[]>(["Create a schedule", "Ask about free time"]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshCalendarStatus();
    const demoMode = new URLSearchParams(window.location.search).get("demo");
    if (!didRunDemo.current && demoMode) {
      didRunDemo.current = true;
      void runDemo(demoMode);
    }
  }, []);

  async function runDemo(mode: string) {
    await submitRequest(sample);
    if (mode === "followup") {
      await submitRequest("What should I do after 7:20pm?");
    }
    if (mode === "modify") {
      await submitRequest("Add dinner at 8pm.");
    }
  }

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
      { id: crypto.randomUUID(), role: "assistant", text: "I am checking your schedule context and working out the best response." }
    ]);

    try {
      const result = await sendAssistantMessage(trimmed);
      if (result.schedule) {
        setSchedule(result.schedule);
        if (result.intent !== "ask_question") {
          setApprovalStatus("draft");
        }
      }
      setSuggestedActions(result.suggested_actions);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: result.assistant_message
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
    void submitRequest(`Regenerate and optimize this schedule. ${lastUserMessage?.text ?? sample}`);
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

  async function handleSync() {
    if (!schedule || isSyncing) {
      return;
    }
    if (!calendarStatus?.configured) {
      appendAssistantMessage("Calendar sync is not connected. Add Google OAuth credentials in backend/.env, then restart the backend.");
      return;
    }
    if (!calendarStatus.authenticated) {
      window.open(googleLoginUrl(), "_blank", "noopener,noreferrer");
      appendAssistantMessage("I opened Google Calendar connection in a new tab. After approving access, come back and press Sync to Calendar again.");
      return;
    }
    setIsSyncing(true);
    try {
      const result = await syncCalendar();
      if (result.created_count > 0) {
        setApprovalStatus("synced");
      }
      appendAssistantMessage(result.message);
      await refreshCalendarStatus();
    } catch (err) {
      appendAssistantMessage(err instanceof Error ? err.message : "Calendar sync failed.");
    } finally {
      setIsSyncing(false);
    }
  }

  async function refreshCalendarStatus() {
    try {
      setCalendarStatus(await getCalendarStatus());
    } catch {
      setCalendarStatus({ authenticated: false, configured: false, message: "Calendar status unavailable." });
    }
  }

  function appendAssistantMessage(text: string) {
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", text }]);
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
              <p>Thinking through your schedule context...</p>
            </article>
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="chatInput">Planning request</label>
          <textarea
            id="chatInput"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask a follow-up, add a task, or plan a new day..."
          />
          <div className="composerActions">
            <button className="secondaryButton" type="button" onClick={() => setInput(sample)}>
              <RefreshCw size={16} />
              Sample
            </button>
            <button type="submit" disabled={isLoading}>
              {isLoading ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
              Send
            </button>
          </div>
          <div className="suggestedActions">
            {suggestedActions.map((action) => (
              <button className="chipButton" type="button" key={action} onClick={() => setInput(action)}>
                {action}
              </button>
            ))}
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
          <button type="button" disabled={!schedule || isSyncing} onClick={handleSync}>
            <CalendarCheck size={16} />
            {isSyncing ? "Syncing" : calendarStatus?.authenticated ? "Sync to Calendar" : "Connect Google Calendar"}
          </button>
        </div>
        <p className="calendarStatus">{calendarStatus?.message ?? "Checking Google Calendar connection..."}</p>

        <SuggestionsPanel
          conflicts={schedule?.conflicts ?? []}
          suggestions={schedule?.suggestions ?? []}
          warnings={schedule?.validation_warnings ?? []}
        />
      </section>
    </main>
  );
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
