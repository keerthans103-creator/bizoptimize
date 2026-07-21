const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:5000";

function authHeaders() {
  const token = localStorage.getItem("bizoptimize_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const response = await fetch(`${GATEWAY_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

export const api = {
  analyzeWorkflow: (workflowText) =>
    request("/api/workflows/analyze", {
      method: "POST",
      body: JSON.stringify({ workflow_text: workflowText }),
    }),

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
