from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
PREDICTIONS_DIR = DATA_DIR / "predictions"
CACHE_DIR = DATA_DIR / "cache"
MIAMI_PREDICTION_FILE = PREDICTIONS_DIR / "miami-2026.json"

FRONTEND_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

