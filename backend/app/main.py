from app.api.v1.books import router as books_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.api.v1.tickets import router as tickets_router
from app.api.v1.events import router as events_router



app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token",
        "Last-Event-ID",
    ],
)

app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)
app.include_router(
    books_router,
    prefix=settings.api_v1_prefix,
)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")