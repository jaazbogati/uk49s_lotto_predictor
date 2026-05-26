# ── Base image ────────────────────────────────────────────────
# Python 3.11 slim keeps the image small
FROM python:3.11-slim

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── System dependencies ───────────────────────────────────────
# psycopg2 needs libpq-dev to connect to PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────
# Copy requirements first — Docker caches this layer
# so rebuilds are fast if only code changed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────
COPY . .

# ── Port ──────────────────────────────────────────────────────
EXPOSE 8000

# ── Startup command ───────────────────────────────────────────
# init_db() creates tables on startup, then uvicorn serves the API
CMD ["sh", "-c", "python -c 'from app.core.database import init_db; init_db()' && uvicorn app.main:app --host 0.0.0.0 --port 8000"]