
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# Bind the platform-provided $PORT (Railway/Render/etc.); fall back to 8080 (Cloud Run's default).
CMD ["sh", "-c", "uvicorn supply_chain_toolset:app --host 0.0.0.0 --port ${PORT:-8080}"]
