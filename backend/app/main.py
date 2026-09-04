from fastapi import FastAPI

from .database import Base, engine
from . import location_models, models  # noqa: F401
from .location_routes import router as location_router
from .routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sentinel API",
    version="0.3.0",
    description="Privacy-first personal safety and device recovery API.",
)

app.include_router(router)
app.include_router(location_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Sentinel API", "status": "ok", "version": "0.3.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
