# Deploys the Google ADK agent's web chat UI (talks to the Railway toolset).
# Build context = repo root. See .railwayignore for what's excluded from upload.
FROM python:3.12-slim

WORKDIR /app

# Slim agent deps only (google-adk, litellm, openai, requests, python-dotenv)
COPY requirements-agent.txt .
RUN pip install --no-cache-dir -r requirements-agent.txt

# Agent package + custom demo front end
COPY supply_chain_agent/ ./supply_chain_agent/
COPY web/ ./web/

# Default toolset target (override via Railway var if needed)
ENV TOOLSET_URL=https://supply-chain-toolset-production.up.railway.app

# OPENAI_API_KEY must be provided as a Railway service variable at runtime.
# Serve the custom landing page (10 example prompts) on Railway's dynamic $PORT.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn web.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
