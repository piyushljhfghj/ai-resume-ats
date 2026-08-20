FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so code edits don't invalidate the pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cache the embedding model into the image so the first request doesn't
# pay a multi-hundred-MB download.
RUN python -c "from app.model_loader import get_model; get_model()"

ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
