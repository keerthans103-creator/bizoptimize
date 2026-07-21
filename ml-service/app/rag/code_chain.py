"""
Retrieval-augmented code generation, built with LangChain.

This is deliberately a separate module from app/rag/vector_store.py, which
handles the score-time "find matching automation write-ups" retrieval used
by /analyze. That retrieval is a single raw chromadb query -- a framework
would only add indirection there. This module does something LangChain is
actually built for: retrieve relevant context, splice it into a prompt
alongside the user's specific task, and generate a new answer from an LLM.
That's a genuine two-step retrieval-augmented-generation chain, so it's
built with LangChain's retriever + LCEL (`retriever | prompt | llm | parser`)
rather than hand-rolled, on purpose.
"""
import json
import os

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

from app.retry import call_with_retry

_CORPUS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "automation_corpus", "corpus.json"
)
_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db_langchain")
_COLLECTION_NAME = "automation_scripts_langchain"

_PROMPT = ChatPromptTemplate.from_template(
    """You are a senior automation engineer. A user wants to automate the following task:

Task: {task}

Here are reference automation patterns retrieved from a knowledge base that are similar to this task:

{context}

Using the reference pattern(s) as a starting point, write a concise, runnable code snippet
(with brief inline comments) that implements automation specifically for the task described above.
Adapt the tools/libraries/approach from the reference pattern(s) to this specific task -- don't just
repeat the reference verbatim. Respond with ONLY the code snippet in a fenced code block, no prose
before or after it.
"""
)

_retriever = None
_chain = None


def _load_corpus() -> list:
    with open(_CORPUS_PATH) as f:
        return json.load(f)


def _get_retriever():
    """Builds (or returns the cached) LangChain retriever over the automation
    corpus. Needs no API key -- safe to call at Docker build time to warm the
    embedding model and pre-populate the vector store."""
    global _retriever
    if _retriever is not None:
        return _retriever

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    os.makedirs(_PERSIST_DIR, exist_ok=True)
    vectorstore = Chroma(
        collection_name=_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=_PERSIST_DIR,
    )

    corpus = _load_corpus()
    existing_ids = vectorstore.get(include=[])["ids"]
    if len(existing_ids) < len(corpus):
        vectorstore.add_texts(
            ids=[entry["id"] for entry in corpus],
            texts=[f"{entry['title']}. {entry['instructions']}" for entry in corpus],
            metadatas=[
                {"title": entry["title"], "category": entry["category"], "instructions": entry["instructions"]}
                for entry in corpus
            ],
        )

    _retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    return _retriever


def warm_up():
    """Populates the vector store without touching the LLM client (which
    requires GEMINI_API_KEY). Called at Docker build time."""
    _get_retriever()


def _format_docs(docs) -> str:
    return "\n\n".join(
        f"- {d.metadata.get('title', '')}: {d.metadata.get('instructions', d.page_content)}" for d in docs
    )


def _get_chain():
    """Builds (or returns the cached) full retrieval-augmented-generation
    chain, including the Gemini LLM client. Only called at request time, once
    GEMINI_API_KEY is actually available."""
    global _chain
    if _chain is not None:
        return _chain

    retriever = _get_retriever()
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.2,
    )

    _chain = (
        RunnableParallel(
            context=retriever | RunnableLambda(_format_docs),
            task=RunnableLambda(lambda x: x),
        )
        | _PROMPT
        | llm
        | StrOutputParser()
    )
    return _chain


def generate_code(task_text: str) -> str:
    """Runs the LangChain retrieval-augmented-generation chain for one task."""
    return call_with_retry(_get_chain().invoke, task_text)
