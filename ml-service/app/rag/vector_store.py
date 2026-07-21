"""
RAG retrieval over the automation-script corpus using an embedded Chroma
instance (no separate vector DB server to run) and Gemini's hosted embeddings
API. Previously used a local sentence-transformers model, but that pulls in
PyTorch and pushed the ml-service container past Render's free-tier 512MB
limit -- calling out to Gemini's API instead keeps the container light at
the cost of a per-embedding network call (fine at this corpus size/traffic).
"""
import json
import os

import chromadb
from google import genai

from app.retry import call_with_retry

_CORPUS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "automation_corpus", "corpus.json"
)
_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
_COLLECTION_NAME = "automation_scripts_gemini"
_EMBEDDING_MODEL = "models/gemini-embedding-001"

_client = None
_collection = None


class _GeminiEmbeddingFunction:
    """chromadb-compatible embedding function backed by Gemini's embeddings API."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Export it before starting ml-service. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        self._genai_client = genai.Client(api_key=api_key)

    def __call__(self, input):
        response = call_with_retry(
            self._genai_client.models.embed_content,
            model=_EMBEDDING_MODEL,
            contents=input,
        )
        return [embedding.values for embedding in response.embeddings]


def _load_corpus() -> list:
    with open(_CORPUS_PATH) as f:
        return json.load(f)


def _get_collection():
    """Lazily builds the Chroma collection, including the Gemini-backed
    embedding function. Deferred (not module-level) so a cold worker process
    doesn't call out to the embeddings API until something actually needs it."""
    global _client, _collection
    if _collection is not None:
        return _collection

    os.makedirs(_PERSIST_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(path=_PERSIST_DIR)
    _collection = _client.get_or_create_collection(
        name=_COLLECTION_NAME, embedding_function=_GeminiEmbeddingFunction()
    )

    # Populate once; corpus.json is small and static, so an ID-count check
    # is enough to avoid re-embedding the whole corpus on every process start.
    corpus = _load_corpus()
    if _collection.count() < len(corpus):
        _collection.upsert(
            ids=[entry["id"] for entry in corpus],
            documents=[
                f"{entry['title']}. {entry['instructions']}" for entry in corpus
            ],
            metadatas=[
                {
                    "title": entry["title"],
                    "category": entry["category"],
                    "instructions": entry["instructions"],
                    "tags": ",".join(entry["tags"]),
                }
                for entry in corpus
            ],
        )
    return _collection


def retrieve_automation(task_text: str, top_k: int = 3) -> list:
    """Return up to top_k best-matching automation script/instruction entries."""
    collection = _get_collection()
    results = collection.query(query_texts=[task_text], n_results=top_k)

    matches = []
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    for entry_id, metadata, distance in zip(ids, metadatas, distances):
        matches.append(
            {
                "id": entry_id,
                "title": metadata["title"],
                "category": metadata["category"],
                "instructions": metadata["instructions"],
                "tags": metadata["tags"].split(",") if metadata["tags"] else [],
                "similarity": round(1 - distance, 4),
            }
        )
    return matches
