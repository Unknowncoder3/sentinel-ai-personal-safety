from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import get_current_user
from .location_models import LocationRecord
from .location_schemas import LocationOut, LocationUpdate
from .models import Device, User

router = APIRouter(prefix="/api/v1/devices", tags=["Location"])


@router.post("/{device_id}/location", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def update_location(
    device_id: UUID,
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.scalar(
        select(Device).where(Device.id == str(device_id), Device.owner_id == current_user.id)
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    recorded_at = payload.recorded_at.astimezone(timezone.utc).replace(tzinfo=None) if payload.recorded_at else now

    record = LocationRecord(
        device_id=device.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        battery_level=payload.battery_level,
        recorded_at=recorded_at,
        received_at=now,
    )

    device.is_online = True
    device.last_latitude = payload.latitude
    device.last_longitude = payload.longitude
    device.battery_level = payload.battery_level
    device.last_seen_at = now

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{device_id}/locations", response_model=list[LocationOut])
def location_history(
    device_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    device = db.scalar(
        select(Device).where(Device.id == str(device_id), Device.owner_id == current_user.id)
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return list(
        db.scalars(
            select(LocationRecord)
            .where(LocationRecord.device_id == device.id)
            .order_by(LocationRecord.recorded_at.desc())
            .limit(limit)
        ).all()
    )
