import { useState } from "react";
import { ArrowRightIcon } from "./icons.jsx";

export default function WorkflowInput({ onAnalyze, loading }) {
  const [text, setText] = useState(
    "Every morning I check the shared inbox and reply to shipping status questions using our template. " +
      "Each Monday I send a reminder email to any customer whose invoice is more than 7 days overdue. " +
      "Once a week I negotiate renewal terms with our two biggest enterprise clients. " +
      "At the end of each month I pull sales numbers from the database and format them into a report for the team."
  );

  return (
    <section className="panel">
      <h2>Describe your workflow</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Paste a plain-text description of what you (or your team) does. We'll split it into
        discrete tasks and score each one's automatability.
      </p>
      <textarea
        rows={8}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Every morning I check the shared inbox and reply to shipping questions..."
      />
      <button disabled={loading || !text.trim()} onClick={() => onAnalyze(text)}>
        {loading ? (
          <>
            <span className="spinner" /> Analyzing
          </>
        ) : (
          <>
            Analyze workflow <ArrowRightIcon size={16} strokeWidth={2.2} />
          </>
        )}
      </button>
    </section>
  );
}
