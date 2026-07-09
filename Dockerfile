FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

# Alibaba Function Compute custom-container listens on 9000 by default; overridable.
ENV PORT=9000
EXPOSE 9000

# QWEN_API_KEY / QWEN_MODEL / SELLER_GSTIN are injected as platform env vars
# (never baked into the image). See DEPLOY.md.
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT}"]
