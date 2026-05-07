import type { ScheduledBlock } from "../types/schedule";

interface TimelineProps {
  blocks: ScheduledBlock[];
}

export function Timeline({ blocks }: TimelineProps) {
  if (!blocks.length) {
    return <div className="emptyState">Your generated schedule will appear here.</div>;
  }

  return (
    <div className="timeline">
      {blocks.map((block) => (
        <div className={`timelineRow ${block.block_type}`} key={block.id}>
          <time>
            {formatTime(block.start)} - {formatTime(block.end)}
          </time>
          <div>
            <strong>{block.title}</strong>
            <span>{block.block_type}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat([], {
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

