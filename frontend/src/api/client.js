const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:5000";

// Render's free tier spins the ml-service/backend down after idle periods;
// the first request after that gets a 502/504 (or a non-JSON body forwarded
// from a still-booting upstream) while it cold-starts, which can take 30-60s.
// Retrying with backoff turns that into a slow-but-successful first request
// instead of a dead-end error for whoever hits the app first.
const COLD_START_STATUSES = new Set([502, 503, 504]);
const COLD_START_RETRY_DELAYS_MS = [3000, 6000, 10000, 15000, 15000];

function isColdStartError(status, data) {
  return COLD_START_STATUSES.has(status) || /non-JSON response/i.test(data?.error || "");
}

function authHeaders() {
  const token = localStorage.getItem("bizoptimize_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}, onRetry) {
  for (let attempt = 0; ; attempt += 1) {
    const response = await fetch(`${GATEWAY_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options.headers || {}),
      },
    });

    const data = await response.json().catch(() => ({}));
    if (response.ok) return data;

    const canRetry = isColdStartError(response.status, data) && attempt < COLD_START_RETRY_DELAYS_MS.length;
    if (!canRetry) {
      throw new Error(data.error || `Request failed with status ${response.status}`);
    }

    onRetry?.(attempt + 1, COLD_START_RETRY_DELAYS_MS.length);
    await new Promise((resolve) => setTimeout(resolve, COLD_START_RETRY_DELAYS_MS[attempt]));
  }
}

export const api = {
  // Fire-and-forget ping to wake the ml-service/backend as early as possible
  // (see gateway's /health). Call this on app mount, not just before Analyze.
  wakeUp: () => fetch(`${GATEWAY_URL}/health`).catch(() => {}),

  analyzeWorkflow: (workflowText, onRetry) =>
    request(
      "/api/workflows/analyze",
      {
        method: "POST",
        body: JSON.stringify({ workflow_text: workflowText }),
      },
      onRetry
    ),

  register: (email, password) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email, password) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  saveWorkflow: (title, rawText, tasks) =>
    request("/api/workflows", {
      method: "POST",
      body: JSON.stringify({ title, rawText, tasks }),
    }),

  listWorkflows: () => request("/api/workflows"),

  getWorkflow: (id) => request(`/api/workflows/${id}`),

  updateTaskSavings: (taskId, hoursPerWeek, hourlyRate) =>
    request(`/api/tasks/${taskId}/savings`, {
      method: "PUT",
      body: JSON.stringify({ hoursPerWeek, hourlyRate }),
    }),

  generateScript: (taskText) =>
    request("/api/tasks/generate-script", {
      method: "POST",
      body: JSON.stringify({ task_text: taskText }),
    }),
};
