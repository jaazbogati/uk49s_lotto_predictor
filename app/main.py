"""
FastAPI Application Entry Point
────────────────────────────────
Initialises the app, registers routes, and runs startup tasks.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.database import init_db

app = FastAPI(
    title       = "UK49s Analytics API",
    description = (
        "Statistical analysis and prediction engine for UK49s draws. "
        "All predictions are for entertainment only — "
        "statistical tests confirm draws are random."
    ),
    version = "1.0.0"
)

# ── CORS ──────────────────────────────────────────────────────
# Allows the React frontend (running on a different port)
# to make requests to this API without being blocked by
# the browser's same-origin policy.

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Startup ───────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Ensures DB tables exist when the server starts."""
    init_db()
    print("[API] Database ready")

# ── Routes ────────────────────────────────────────────────────

app.include_router(router, prefix="/api/v1")

# ── Root ──────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "UK49s Analytics API",
        "version": "1.0.0",
        "docs":    "/docs",
        "status":  "running"
    }