"""
ML service entrypoint. Exposes NLP parsing, Random Forest scoring, and RAG
retrieval as HTTP endpoints. This service does not talk to Postgres directly
-- persistence is the Java backend's job; the Flask gateway orchestrates
calls between the two (see /gateway).
"""
import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from app.nlp.workflow_parser import WorkflowParserError, parse_workflow
from app.nlp.feature_extractor import extract_features
from app.rag.code_chain import generate_code
from app.rag.vector_store import retrieve_automation
from app.scoring.classifier import ModelNotTrainedError, score_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTOMATABILITY_THRESHOLD = 70

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/parse")
def parse():
    body = request.get_json(force=True) or {}
    workflow_text = (body.get("workflow_text") or "").strip()
    if not workflow_text:
        return jsonify({"error": "workflow_text is required"}), 400

    try:
        tasks = parse_workflow(workflow_text)
    except WorkflowParserError as exc:
        logger.exception("Workflow parsing failed")
        return jsonify({"error": str(exc)}), 502

    return jsonify({"tasks": tasks})


@app.post("/score")
def score():
    body = request.get_json(force=True) or {}
    task_text = (body.get("task_text") or "").strip()
    if not task_text:
        return jsonify({"error": "task_text is required"}), 400

    features = extract_features(task_text)
    try:
        result = score_task(features)
    except ModelNotTrainedError as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify(result)


@app.post("/retrieve")
def retrieve():
    body = request.get_json(force=True) or {}
    task_text = (body.get("task_text") or "").strip()
    top_k = int(body.get("top_k", 3))
    if not task_text:
        return jsonify({"error": "task_text is required"}), 400

    matches = retrieve_automation(task_text, top_k=top_k)
    return jsonify({"matches": matches})


@app.post("/generate-script")
def generate_script():
    """Retrieval-augmented code generation for one task, built with LangChain.

    Separate from /retrieve: that endpoint returns the matched instructional
    write-up as-is, this one feeds that context plus the task's exact wording
    to Gemini to generate a tailored code snippet.
    """
    body = request.get_json(force=True) or {}
    task_text = (body.get("task_text") or "").strip()
    if not task_text:
        return jsonify({"error": "task_text is required"}), 400

    try:
        code = generate_code(task_text)
    except Exception as exc:
        logger.exception("Code generation failed")
        return jsonify({"error": str(exc)}), 502

    return jsonify({"code": code})


@app.post("/analyze")
def analyze():
    """Full pipeline for one workflow: parse -> score each task -> RAG for 70+.

    This is the endpoint the Flask gateway calls for the main "score my
    workflow" user action.
    """
    body = request.get_json(force=True) or {}
    workflow_text = (body.get("workflow_text") or "").strip()
    if not workflow_text:
        return jsonify({"error": "workflow_text is required"}), 400

    try:
        parsed_tasks = parse_workflow(workflow_text)
    except WorkflowParserError as exc:
        logger.exception("Workflow parsing failed")
        return jsonify({"error": str(exc)}), 502

    analyzed = []
    for task in parsed_tasks:
        task_text = task["text"]
        features = extract_features(task_text)
        try:
            scored = score_task(features)
        except ModelNotTrainedError as exc:
            return jsonify({"error": str(exc)}), 503

        entry = {
            "task_text": task_text,
            "hint": task.get("hint", ""),
            "score": scored["score"],
            "explanation": scored["explanation"],
            "features": scored["features"],
            "automation": [],
        }
        if scored["score"] >= AUTOMATABILITY_THRESHOLD:
            entry["automation"] = retrieve_automation(task_text, top_k=3)
        analyzed.append(entry)

    analyzed.sort(key=lambda t: t["score"], reverse=True)
    return jsonify({"tasks": analyzed, "threshold": AUTOMATABILITY_THRESHOLD})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
