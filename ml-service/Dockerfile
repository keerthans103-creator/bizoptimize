FROM python:3.11-slim

WORKDIR /app

# System deps for scikit-learn/spaCy wheels
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

# Bake the Random Forest and pre-populate the Chroma vector store at build
# time so the container starts ready to serve, instead of doing this work
# (and downloading the embedding model) on the first incoming request.
RUN python models/train_model.py
RUN python -c "from app.rag.vector_store import retrieve_automation; retrieve_automation('warm up the index')"
RUN python -c "from app.rag.code_chain import warm_up; warm_up()"

ENV PORT=5001
ENV PYTHONPATH=/app
EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120", "app.main:app"]
