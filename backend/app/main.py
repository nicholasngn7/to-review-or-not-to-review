"""MR Review Council — FastAPI application entrypoint.

This is the scaffold step: the app only exposes a health check. Diff parsing,
the mock review engine, and the review endpoint are added in later phases.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.routes import diff_router, reviews_router

# Local dev origins for the Vite frontend.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(
    title="MR Review Council API",
    description="Multi-persona AI merge-request reviewer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diff_router)
app.include_router(reviews_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness probe used by local dev and future infra checks."""
    return HealthResponse(status="ok")
