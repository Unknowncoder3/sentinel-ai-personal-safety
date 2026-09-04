from fastapi import FastAPI

app = FastAPI(
    title="Sentinel API",
    version="0.1.0",
    description="Privacy-first personal safety and device recovery API.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Sentinel API", "status": "ok", "version": "0.1.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
