"""
Flask API gateway -- the single entry point the React frontend talks to.

Routes requests to either the Spring Boot backend (auth, persistence, CRUD)
or the Python ML service (parsing, scoring, RAG retrieval), and orchestrates
calls that need both, e.g. "analyze this workflow" (ML service) followed by
"save these results" (Java backend) are two separate calls the frontend can
make back-to-back through this gateway, but /api/workflows/full-save shows
the gateway doing that orchestration itself in one round trip.
"""
import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:5001")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8080")
REQUEST_TIMEOUT = 60

app = Flask(__name__)
CORS(app)


def _forward_headers():
    # Only forward the Authorization header onward -- not the full incoming
    # header set -- so the gateway doesn't leak client-only headers (Host,
    # Origin, cookies) into service-to-service calls.
    auth = request.headers.get("Authorization")
    return {"Authorization": auth} if auth else {}


def _proxy(method, base_url, path, **kwargs):
    try:
        resp = requests.request(
            method, f"{base_url}{path}", timeout=REQUEST_TIMEOUT, **kwargs
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"{base_url} is unreachable"}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": f"{base_url}{path} timed out"}), 504

    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": "non-JSON response from upstream service"}
    return jsonify(payload), resp.status_code


@app.get("/health")
def health():
    return jsonify({"status": "ok", "gateway": "up"})


# ---- ML service routes ----------------------------------------------------

@app.post("/api/workflows/analyze")
def analyze_workflow():
    """Parse + score + RAG-retrieve for a raw workflow description. Stateless
    -- does not persist anything. The frontend calls /api/workflows to save
    the result afterward."""
    body = request.get_json(force=True) or {}
    return _proxy("POST", ML_SERVICE_URL, "/analyze", json=body)


@app.post("/api/tasks/score")
def score_single_task():
    body = request.get_json(force=True) or {}
    return _proxy("POST", ML_SERVICE_URL, "/score", json=body)


@app.post("/api/tasks/automation")
def retrieve_automation():
    body = request.get_json(force=True) or {}
    return _proxy("POST", ML_SERVICE_URL, "/retrieve", json=body)


@app.post("/api/tasks/generate-script")
def generate_script():
    """Retrieval-augmented code generation (LangChain chain in ml-service)."""
    body = request.get_json(force=True) or {}
    return _proxy("POST", ML_SERVICE_URL, "/generate-script", json=body)


# ---- Java backend routes (auth, persistence) -------------------------------

@app.post("/api/auth/register")
def register():
    body = request.get_json(force=True) or {}
    return _proxy("POST", BACKEND_URL, "/api/auth/register", json=body)


@app.post("/api/auth/login")
def login():
    body = request.get_json(force=True) or {}
    return _proxy("POST", BACKEND_URL, "/api/auth/login", json=body)


@app.get("/api/workflows")
def list_workflows():
    return _proxy("GET", BACKEND_URL, "/api/workflows", headers=_forward_headers())


@app.get("/api/workflows/<int:workflow_id>")
def get_workflow(workflow_id):
    return _proxy(
        "GET", BACKEND_URL, f"/api/workflows/{workflow_id}", headers=_forward_headers()
    )


@app.post("/api/workflows")
def save_workflow():
    """Persist an already-analyzed workflow (title, raw text, scored tasks)."""
    body = request.get_json(force=True) or {}
    return _proxy(
        "POST", BACKEND_URL, "/api/workflows", json=body, headers=_forward_headers()
    )


@app.put("/api/tasks/<int:task_id>/savings")
def update_task_savings(task_id):
    """Forward user-entered hours/week + hourly rate so the Java backend can
    compute and persist the ROI projection for one saved task."""
    body = request.get_json(force=True) or {}
    return _proxy(
        "PUT",
        BACKEND_URL,
        f"/api/tasks/{task_id}/savings",
        json=body,
        headers=_forward_headers(),
    )


# ---- Orchestrated route: analyze + save in a single round trip ------------

@app.post("/api/workflows/full-save")
def analyze_and_save():
    """Convenience endpoint: analyze a raw workflow via ML service, then
    immediately persist the result via the Java backend. Requires auth."""
    body = request.get_json(force=True) or {}
    workflow_text = body.get("workflow_text", "")

    try:
        analyze_resp = requests.post(
            f"{ML_SERVICE_URL}/analyze",
            json={"workflow_text": workflow_text},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"ML service call failed: {exc}"}), 502

    if analyze_resp.status_code != 200:
        return jsonify(analyze_resp.json()), analyze_resp.status_code

    analyzed = analyze_resp.json()
    save_payload = {
        "title": body.get("title", "Untitled workflow"),
        "rawText": workflow_text,
        "tasks": analyzed["tasks"],
    }

    try:
        save_resp = requests.post(
            f"{BACKEND_URL}/api/workflows",
            json=save_payload,
            headers=_forward_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Backend save failed: {exc}"}), 502

    try:
        payload = save_resp.json()
    except ValueError:
        payload = {"error": "non-JSON response from backend"}
    return jsonify(payload), save_resp.status_code


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
