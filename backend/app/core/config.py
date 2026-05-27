from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CACHE_DIR = BASE_DIR / "data" / "fastf1_cache"
MIAMI_PREDICTION_FILE = BASE_DIR / "data" / "predictions" / "miami-2026.json"
SITE_DATA_FILE = BASE_DIR / "data" / "site_data.json"

# Auto-create directories so Render doesn't crash
CACHE_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data" / "predictions").mkdir(parents=True, exist_ok=True)