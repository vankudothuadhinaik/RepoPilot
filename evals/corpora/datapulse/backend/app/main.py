import os
import secrets

from fastapi import Header, HTTPException

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Event
from .schemas import EventIn, Metrics

app = FastAPI(title="DataPulse Analytics API", version="1.0.0")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require a configured API key outside local development.

    Set DATAPULSE_API_KEY to protect ingestion and analytics routes. In a
    production environment, refusing requests without a configured key avoids
    accidentally exposing the demo API with authentication disabled.
    """
    expected = os.getenv("DATAPULSE_API_KEY")
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    if not expected:
        if environment in {"production", "prod"}:
            raise HTTPException(status_code=503, detail="API authentication is not configured")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# Keep automatic schema creation local-only. Production schema changes must be
# applied by the release migration step (alembic upgrade head), not each API worker.
if os.getenv("ENVIRONMENT", "development").strip().lower() not in {"production", "prod"}:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Report readiness only when the database dependency can answer a query."""
    try:
        db.execute(select(1))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "dependency": "database"},
        )
    return {"status": "ready"}


@app.post("/events", status_code=201, dependencies=[Depends(require_api_key)])
def ingest(event: EventIn, db: Session = Depends(get_db)) -> dict[str, int]:
    obj = Event(**event.model_dump(exclude_none=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id}


@app.get("/analytics/metrics", response_model=Metrics, dependencies=[Depends(require_api_key)])
def metrics(db: Session = Depends(get_db)) -> Metrics:
    return Metrics(
        events=db.scalar(select(func.count(Event.id))) or 0,
        users=db.scalar(select(func.count(func.distinct(Event.user_id)))) or 0,
        sessions=db.scalar(select(func.count(func.distinct(Event.session_id)))) or 0,
        revenue=float(db.scalar(select(func.coalesce(func.sum(Event.value), 0))) or 0),
    )


@app.get("/analytics/top-events", dependencies=[Depends(require_api_key)])
def top_events(db: Session = Depends(get_db)) -> list[dict[str, int | str]]:
    rows = db.execute(
        select(Event.event_name, func.count(Event.id).label("count"))
        .group_by(Event.event_name)
        .order_by(func.count(Event.id).desc(), Event.event_name.asc())
        .limit(10)
    ).all()
    return [{"event": row.event_name, "count": row.count} for row in rows]
