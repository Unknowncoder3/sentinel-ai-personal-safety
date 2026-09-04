from datetime import datetime

from pydantic import BaseModel, Field


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    battery_level: float | None = Field(default=None, ge=0, le=100)
    recorded_at: datetime | None = None


class LocationOut(LocationUpdate):
    id: str
    device_id: str
    received_at: datetime
