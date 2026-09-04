from datetime import datetime

from pydantic import BaseModel, Field


class GuardianCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = None


class GuardianOut(GuardianCreate):
    id: str
    created_at: datetime


class SOSCreate(BaseModel):
    device_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    message: str | None = Field(default=None, max_length=1000)


class SOSOut(BaseModel):
    id: str
    device_id: str | None
    status: str
    latitude: float | None
    longitude: float | None
    message: str | None
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
