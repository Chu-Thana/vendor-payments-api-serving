from fastapi import FastAPI

from app.api.health import router as health_router


app = FastAPI(
    title="Vendor Payments API",
    description=(
        "API serving layer for trusted Vendor Payments "
        "batch and streaming analytics data."
    ),
    version="1.0.0",
)

app.include_router(health_router)


@app.get("/", tags=["Root"])
def get_root() -> dict[str, str]:
    return {
        "message": "Vendor Payments API is running",
        "docs": "/docs",
    }