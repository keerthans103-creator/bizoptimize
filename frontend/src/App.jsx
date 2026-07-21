import { useState } from "react";
import { api } from "./api/client.js";
import HistoryPage from "./components/HistoryPage.jsx";
import SavingsSummary from "./components/SavingsSummary.jsx";
import Sidebar from "./components/Sidebar.jsx";
import TaskFeed from "./components/TaskFeed.jsx";
import TaskList from "./components/TaskList.jsx";
import WorkflowInput from "./components/WorkflowInput.jsx";

const TOPBAR_TITLES = {
  analyze: "New analysis",
  feed: "Feed",
  summary: "Summary",
  history: "Saved workflows",
};

function toInternalTask(mlTask) {
  return {
    text: mlTask.task_text,
    hint: mlTask.hint,
    score: mlTask.score,
    explanation: mlTask.explanation,
    features: mlTask.features,
    automation: mlTask.automation,
    id: null,
    hoursPerWeek: null,
    hourlyRate: null,
    estimatedAnnualSavings: null,
  };
}

function toInternalTaskFromSaved(saved) {
  return {
    text: saved.taskText,
    hint: saved.hint,
    score: saved.score,
    explanation: saved.explanation,
    features: saved.features,
    automation: saved.automation,
    id: saved.id,
    hoursPerWeek: saved.hoursPerWeek,
    hourlyRate: saved.hourlyRate,
    estimatedAnnualSavings: saved.estimatedAnnualSavings,
  };
}

// decisions maps task.text -> "automate" | "skip", lifted up to App so both
// Feed (where decisions are made) and the save payload (which persists them)
// share one source of truth.
function toBackendTaskShape(task, decisions) {
  const decision = decisions[task.text];
  return {
    task_text: task.text,
    hint: task.hint,
    score: task.score,
    explanation: task.explanation,
    features: task.features,
    automation: task.automation,
    automation_decision: decision ? decision.toUpperCase() : null,
  };
}

export default function App() {
  const [view, setView] = useState("analyze");
  const [email, setEmail] = useState(localStorage.getItem("bizoptimize_email"));
  const [rawText, setRawText] = useState("");
  const [tasks, setTasks] = useState([]);
  const [savingsByTask, setSavingsByTask] = useState({});
  const [decisionsByTaskText, setDecisionsByTaskText] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [workflowId, setWorkflowId] = useState(null);
  const [title, setTitle] = useState("");
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const resetAnalysis = () => {
    setRawText("");
    setTasks([]);
    setSavingsByTask({});
    setDecisionsByTaskText({});
    setWorkflowId(null);
    setTitle("");
    setError("");
    setView("analyze");
  };

  const handleNavigate = (nextView) => {
    setError("");
    setView(nextView);
  };

  const handleAnalyze = async (text) => {
    setLoading(true);
    setError("");
    setWorkflowId(null);
    try {
      const { tasks: mlTasks } = await api.analyzeWorkflow(text);
      setRawText(text);
      setTasks(mlTasks.map(toInternalTask));
      setTitle(text.slice(0, 60));
      setSavingsByTask({});
      setDecisionsByTaskText({});
      setView("feed");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSavingsChange = (task, hours, rate) => {
    const estimate = Math.round(hours * 52 * rate * (task.score / 100) * 100) / 100;
    setSavingsByTask((prev) => ({ ...prev, [task.text]: estimate }));
  };

  const handlePersistSavings = async (taskId, hours, rate) => {
    try {
      const updated = await api.updateTaskSavings(taskId, hours, rate);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? toInternalTaskFromSaved(updated) : t)));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTaskDecide = (taskText, decision) => {
    setDecisionsByTaskText((prev) => ({ ...prev, [taskText]: decision }));
  };

  const handleRestartDecisions = () => {
    setDecisionsByTaskText({});
  };

  const handleSave = async () => {
    setError("");
    try {
      const response = await api.saveWorkflow(
        title || "Untitled workflow",
        rawText,
        tasks.map((t) => toBackendTaskShape(t, decisionsByTaskText))
      );
      setWorkflowId(response.id);
      setTasks(response.tasks.map(toInternalTaskFromSaved));
      setHistoryRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectHistory = async (id) => {
    setError("");
    try {
      const workflow = await api.getWorkflow(id);
      setWorkflowId(workflow.id);
      setTitle(workflow.title);
      setRawText(workflow.rawText);
      setTasks(workflow.tasks.map(toInternalTaskFromSaved));
      setSavingsByTask({});

      const restoredDecisions = {};
      workflow.tasks.forEach((t) => {
        if (t.automationDecision) {
          restoredDecisions[t.taskText] = t.automationDecision.toLowerCase();
        }
      });
      setDecisionsByTaskText(restoredDecisions);

      setView("summary");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="shell">
      <Sidebar view={view} onNavigate={handleNavigate} email={email} onAuthChange={setEmail} />

      <div className="main">
        <div className="topbar">
          <h2>{TOPBAR_TITLES[view]}</h2>
          {tasks.length > 0 && view !== "history" && (
            <button className="btn-secondary" onClick={resetAnalysis}>
              Start over
            </button>
          )}
        </div>

        <div className={`content ${view === "analyze" ? "center-empty" : ""}`}>
          <div className="content-column">
            {error && <div className="error-banner">{error}</div>}

            {view === "feed" && tasks.length === 0 && (
              <div className="error-banner">
                Run an analysis first, then come back to Feed to swipe through the ranked tasks.
              </div>
            )}

            {view === "history" && (
              <HistoryPage
                isLoggedIn={!!email}
                onSelect={handleSelectHistory}
                refreshKey={historyRefreshKey}
              />
            )}

            {view === "analyze" && <WorkflowInput onAnalyze={handleAnalyze} loading={loading} />}

            {view === "summary" &&
              (tasks.length === 0 ? (
                <div className="error-banner">Run an analysis first to see its summary here.</div>
              ) : (
                <>
                  <section className="panel">
                    <h2>Name this workflow</h2>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Name this workflow"
                    />
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <button disabled={!email} onClick={handleSave}>
                        {email ? "Save workflow" : "Sign in to save"}
                      </button>
                      {workflowId && <span className="muted small">Saved &middot; id {workflowId}</span>}
                    </div>
                  </section>

                  <SavingsSummary tasks={tasks} savingsByTask={savingsByTask} />
                  <TaskList
                    tasks={tasks}
                    decisions={decisionsByTaskText}
                    onSavingsChange={handleSavingsChange}
                    onPersistSavings={handlePersistSavings}
                  />
                </>
              ))}
          </div>
        </div>
      </div>

      {view === "feed" && tasks.length > 0 && (
        <TaskFeed
          tasks={tasks}
          decisions={decisionsByTaskText}
          onDecide={handleTaskDecide}
          onRestartDecisions={handleRestartDecisions}
          onExit={() => setView("summary")}
        />
      )}
    </div>
  );
}
