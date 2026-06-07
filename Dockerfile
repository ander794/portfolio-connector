# Container image for the Portfolio Insights Claude connector.
# Works on any free container host (Render, Fly.io, Hugging Face Spaces, etc.).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY views/ ./views/

# Hosts inject $PORT; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
