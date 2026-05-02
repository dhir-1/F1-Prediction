from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CACHE_DIR = BASE_DIR / "data" / "fastf1_cache"
MIAMI_PREDICTION_FILE = BASE_DIR / "data" / "predictions" / "miami-2026.json"
SITE_DATA_FILE = BASE_DIR / "data" / "site_data.json"