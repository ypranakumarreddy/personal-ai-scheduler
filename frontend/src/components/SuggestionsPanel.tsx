interface SuggestionsPanelProps {
  conflicts: string[];
  suggestions: string[];
  warnings: string[];
}

export function SuggestionsPanel({ conflicts, suggestions, warnings }: SuggestionsPanelProps) {
  const items = [
    ...conflicts.map((message) => ({ kind: "Conflict", message })),
    ...suggestions.map((message) => ({ kind: "Suggestion", message })),
    ...warnings.map((message) => ({ kind: "Warning", message }))
  ];

  return (
    <aside className="sidePanel">
      <div className="panelHeader">
        <span>AI Suggestions</span>
        <strong>{items.length}</strong>
      </div>
      {items.length === 0 ? (
        <p className="muted">No conflicts yet. Generate a schedule to review recommendations.</p>
      ) : (
        <ul>
          {items.map((item, index) => (
            <li key={`${item.kind}-${index}`}>
              <small>{item.kind}</small>
              <span>{item.message}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

