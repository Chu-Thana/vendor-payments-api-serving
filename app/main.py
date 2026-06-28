import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.metadata import router as metadata_router
from app.api.batch import router as batch_router
from app.api.streaming import router as streaming_router
from app.middleware.observability import ObservabilityMiddleware


def get_cors_origins() -> list[str]:
    default_origins = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    return [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", default_origins).split(",")
        if origin.strip()
    ]


app = FastAPI(
    title="Vendor Payments API",
    description=(
        "API serving layer for trusted Vendor Payments "
        "batch and streaming analytics data."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(ObservabilityMiddleware)

app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(batch_router)
app.include_router(streaming_router)


@app.get("/", tags=["Root"])
def get_root() -> dict[str, str]:
    return {
        "message": "Vendor Payments API is running",
        "docs": "/docs",
    }