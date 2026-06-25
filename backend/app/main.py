"""MR Review Council — FastAPI application entrypoint.

This is the scaffold step: the app only exposes a health check. Diff parsing,
the mock review engine, and the review endpoint are added in later phases.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.routes import (
    diff_router,
    import_comments_router,
    retrieve_context_router,
    reviews_router,
)

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
app.include_router(import_comments_router)
app.include_router(retrieve_context_router)


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(
    request: Request, exc: NotImplementedError
) -> JSONResponse:
    """Surface not-yet-implemented providers (e.g. Bedrock) as a clear 501.

    Without this, an unimplemented provider would return an opaque 500. A 501
    with the explanatory message makes the deferred integration obvious.
    """
    return JSONResponse(status_code=501, content={"detail": str(exc)})


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness probe used by local dev and future infra checks."""
    return HealthResponse(status="ok")
