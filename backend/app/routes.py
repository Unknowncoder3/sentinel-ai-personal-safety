from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import get_current_user
from .models import Device, User
from .schemas import DeviceCreate, DeviceOut, Token, UserCreate, UserOut
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1")


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.id))


@router.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.scalar(select(Device).where(Device.device_identifier == payload.device_identifier))
    if existing:
        raise HTTPException(status_code=409, detail="Device identifier is already registered")

    device = Device(
        owner_id=current_user.id,
        name=payload.name,
        platform=payload.platform,
        device_identifier=payload.device_identifier,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Device).where(Device.owner_id == current_user.id)).all())
