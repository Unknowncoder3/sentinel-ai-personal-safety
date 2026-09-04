from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import location_models, models  # noqa: F401
from .location_routes import router as location_router
from .routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sentinel API",
    version="0.3.1",
    description="Privacy-first personal safety and device recovery API.",
)

# MVP dashboard access. Tighten this list for production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(location_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Sentinel API", "status": "ok", "version": "0.3.1"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
