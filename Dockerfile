# ── Base image ────────────────────────────────────────────────────────
# Python 3.11 slim keeps the image small while still supporting all deps.
FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────
# psutil is pure Python + C — no system-level packet capture libs needed.
# A minimal apt update is still run to keep the base image up to date.
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────
# Copy requirements first so Docker can cache this layer.
# Re-runs only when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Project files ─────────────────────────────────────────────────────
COPY src/        ./src/
COPY tests/      ./tests/
COPY templates/  ./templates/
COPY static/     ./static/
COPY data/       ./data/
COPY notebooks/  ./notebooks/

# ── Port ──────────────────────────────────────────────────────────────
EXPOSE 5000

# ── Start ─────────────────────────────────────────────────────────────
# Run from /app (project root) so all relative paths resolve correctly.
CMD ["python", "tests/run_live_web_dashboard.py"]
