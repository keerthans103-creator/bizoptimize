FROM python:3.11-slim

WORKDIR /app

# System deps for scikit-learn/spaCy wheels
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

# Bake the Random Forest at build time (no API key needed). The Chroma
# vector stores are no longer warmed here -- they're embedded via Gemini's
# API now instead of a local model, and GEMINI_API_KEY isn't available at
# build time, so that population happens lazily on first request instead.
RUN python models/train_model.py

ENV PORT=5001
ENV PYTHONPATH=/app
EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--timeout", "120", "app.main:app"]
