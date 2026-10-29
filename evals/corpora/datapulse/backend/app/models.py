from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_time_name", "occurred_at", "event_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_name: Mapped[str] = mapped_column(String(80), index=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    session_id: Mapped[str] = mapped_column(String(120), index=True)
    country: Mapped[str] = mapped_column(
        String(80), default="Unknown", server_default="Unknown", index=True
    )
    device: Mapped[str] = mapped_column(
        String(40), default="desktop", server_default="desktop"
    )
    value: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
