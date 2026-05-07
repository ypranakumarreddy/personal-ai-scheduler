import { CalendarCheck, Loader2, RefreshCw, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";

import { generateSchedule } from "./api/schedules";
import { SuggestionsPanel } from "./components/SuggestionsPanel";
import { Timeline } from "./components/Timeline";
import type { ScheduleResponse } from "./types/schedule";

const sample =
  "Tomorrow wake up at 6am, gym at 7am, office at 9am, interview at 12:30pm, parents call for 20 mins, study 2 hours, sleep by 10:30pm.";

export default function App() {
  const [input, setInput] = useState(sample);
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("demo") === "1") {
      void handleGenerate();
    }
  }, []);

  async function handleGenerate() {
    setIsLoading(true);
    setError(null);
    try {
      setSchedule(await generateSchedule(input));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="appShell">
      <section className="workspace">
        <header className="topBar">
          <div>
            <h1>Personal AI Scheduling Assistant</h1>
            <p>Workflow automation for planning, conflict resolution, and calendar-ready schedules.</p>
          </div>
          <button className="iconButton" type="button" onClick={handleGenerate} disabled={isLoading} title="Generate schedule">
            {isLoading ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
            <span>{isLoading ? "Optimizing" : "Optimize"}</span>
          </button>
        </header>

        <div className="commandCenter">
          <label htmlFor="request">Natural language request</label>
          <textarea id="request" value={input} onChange={(event) => setInput(event.target.value)} />
          <div className="actions">
            <button type="button" onClick={() => setInput(sample)}>
              <RefreshCw size={16} />
              Reset
            </button>
            <button type="button" onClick={handleGenerate} disabled={isLoading}>
              <CalendarCheck size={16} />
              Build Schedule
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>

        <section className="timelineSection">
          <div className="sectionTitle">
            <h2>{schedule ? `Schedule for ${schedule.target_date}` : "Daily Timeline"}</h2>
            <span>{schedule?.calendar_sync_status ?? "Calendar sync idle"}</span>
          </div>
          <Timeline blocks={schedule?.timeline ?? []} />
        </section>
      </section>

      <SuggestionsPanel
        conflicts={schedule?.conflicts ?? []}
        suggestions={schedule?.suggestions ?? []}
        warnings={schedule?.validation_warnings ?? []}
      />
    </main>
  );
}
