from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonBlankEventName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
NonBlankUserId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
NonBlankSessionId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
NonBlankCountry = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
NonBlankDevice = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_name: NonBlankEventName
    user_id: NonBlankUserId
    session_id: NonBlankSessionId
    country: NonBlankCountry = "Unknown"
    device: NonBlankDevice = "desktop"
    value: float = Field(default=0, ge=0, allow_inf_nan=False)
    occurred_at: datetime | None = None


class Metrics(BaseModel):
    events: int
    users: int
    sessions: int
    revenue: float
