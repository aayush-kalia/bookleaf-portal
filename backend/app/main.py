from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }