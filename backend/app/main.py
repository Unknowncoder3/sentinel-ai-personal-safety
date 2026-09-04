from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import journey_models, location_models, models, notification_models, safety_models  # noqa: F401
from .journey_routes import router as journey_router
from .location_routes import router as location_router
from .routes import router
from .safety_routes import router as safety_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sentinel API",
    version="0.6.0",
    description="Privacy-first personal safety and device recovery API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(location_router)
app.include_router(safety_router)
app.include_router(journey_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Sentinel API", "status": "ok", "version": "0.6.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
