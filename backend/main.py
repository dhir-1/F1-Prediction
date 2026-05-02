from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import site_data
from pathlib import Path

app = FastAPI(title="Dhir's Pit Wall API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(site_data.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug-path")
def debug_path():
    from app.core.config import CACHE_DIR
    predictions_dir = CACHE_DIR.parent / "predictions"
    files = list(predictions_dir.glob("*.json")) if predictions_dir.exists() else []
    return {
        "predictions_dir": str(predictions_dir),
        "exists": predictions_dir.exists(),
        "files": [str(f) for f in files]
    }




@app.get("/clear-cache")
def clear_cache():
    from app.api.site_data import _cache
    _cache["data"] = None
    _cache["timestamp"] = 0
    return {"status": "cache cleared"}