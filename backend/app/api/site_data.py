import time
import json
import fastf1
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.core.config import CACHE_DIR, SITE_DATA_FILE

router = APIRouter()

# ── In-memory cache ───────────────────────────────────────────────────────────
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 3600 # 1 hour

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


# ── 2026 Race Schedule (static — won't change mid-season) ────────────────────
RACE_SCHEDULE = [
    {"round": 1,  "slug": "australia-2026",  "name": "Australian Grand Prix",  "country": "Australia",   "flag": "🇦🇺", "circuit": "Albert Park Circuit",                "date": "2026-03-15T05:00:00Z", "laps": 58, "lengthKm": 5.278},
    {"round": 2,  "slug": "china-2026",      "name": "Chinese Grand Prix",      "country": "China",       "flag": "🇨🇳", "circuit": "Shanghai International Circuit",     "date": "2026-03-22T07:00:00Z", "laps": 56, "lengthKm": 5.451},
    {"round": 3,  "slug": "japan-2026",      "name": "Japanese Grand Prix",     "country": "Japan",       "flag": "🇯🇵", "circuit": "Suzuka International Racing Course",  "date": "2026-04-06T05:00:00Z", "laps": 53, "lengthKm": 5.807},
    {"round": 4,  "slug": "bahrain-2026",    "name": "Bahrain Grand Prix",      "country": "Bahrain",     "flag": "🇧🇭", "circuit": "Bahrain International Circuit",       "date": "2026-04-19T15:00:00Z", "laps": 57, "lengthKm": 5.412, "status": "cancelled", "note": "Cancelled due to conflict in the Middle East"},
    {"round": 5,  "slug": "saudi-2026",      "name": "Saudi Arabian Grand Prix","country": "Saudi Arabia","flag": "🇸🇦", "circuit": "Jeddah Corniche Circuit",             "date": "2026-04-26T17:00:00Z", "laps": 50, "lengthKm": 6.174, "status": "cancelled", "note": "Cancelled due to conflict in the Middle East"},
    {"round": 6,  "slug": "miami-2026",      "name": "Miami Grand Prix",        "country": "USA",         "flag": "🇺🇸", "circuit": "Miami International Autodrome",       "date": "2026-05-04T20:00:00Z", "laps": 57, "lengthKm": 5.412},
    {"round": 7,  "slug": "imola-2026",      "name": "Emilia Romagna Grand Prix","country": "Italy",      "flag": "🇮🇹", "circuit": "Autodromo Enzo e Dino Ferrari",       "date": "2026-05-17T13:00:00Z", "laps": 63, "lengthKm": 4.909},
    {"round": 8,  "slug": "monaco-2026",     "name": "Monaco Grand Prix",       "country": "Monaco",      "flag": "🇲🇨", "circuit": "Circuit de Monaco",                  "date": "2026-05-24T13:00:00Z", "laps": 78, "lengthKm": 3.337},
    {"round": 9,  "slug": "spain-2026",      "name": "Spanish Grand Prix",      "country": "Spain",       "flag": "🇪🇸", "circuit": "Circuit de Barcelona-Catalunya",      "date": "2026-06-07T13:00:00Z", "laps": 66, "lengthKm": 4.657},
    {"round": 10, "slug": "canada-2026",     "name": "Canadian Grand Prix",     "country": "Canada",      "flag": "🇨🇦", "circuit": "Circuit Gilles Villeneuve",           "date": "2026-06-14T18:00:00Z", "laps": 70, "lengthKm": 4.361},
    {"round": 11, "slug": "austria-2026",    "name": "Austrian Grand Prix",     "country": "Austria",     "flag": "🇦🇹", "circuit": "Red Bull Ring",                       "date": "2026-06-28T13:00:00Z", "laps": 71, "lengthKm": 4.318},
    {"round": 12, "slug": "britain-2026",    "name": "British Grand Prix",      "country": "UK",          "flag": "🇬🇧", "circuit": "Silverstone Circuit",                 "date": "2026-07-05T14:00:00Z", "laps": 52, "lengthKm": 5.891},
    {"round": 13, "slug": "belgium-2026",    "name": "Belgian Grand Prix",      "country": "Belgium",     "flag": "🇧🇪", "circuit": "Circuit de Spa-Francorchamps",        "date": "2026-07-26T13:00:00Z", "laps": 44, "lengthKm": 7.004},
    {"round": 14, "slug": "hungary-2026",    "name": "Hungarian Grand Prix",    "country": "Hungary",     "flag": "🇭🇺", "circuit": "Hungaroring",                         "date": "2026-08-02T13:00:00Z", "laps": 70, "lengthKm": 4.381},
    {"round": 15, "slug": "netherlands-2026","name": "Dutch Grand Prix",        "country": "Netherlands", "flag": "🇳🇱", "circuit": "Circuit Zandvoort",                   "date": "2026-08-30T13:00:00Z", "laps": 72, "lengthKm": 4.259},
    {"round": 16, "slug": "italy-2026",      "name": "Italian Grand Prix",      "country": "Italy",       "flag": "🇮🇹", "circuit": "Autodromo Nazionale Monza",           "date": "2026-09-06T13:00:00Z", "laps": 53, "lengthKm": 5.793},
    {"round": 17, "slug": "azerbaijan-2026", "name": "Azerbaijan Grand Prix",   "country": "Azerbaijan",  "flag": "🇦🇿", "circuit": "Baku City Circuit",                   "date": "2026-09-20T11:00:00Z", "laps": 51, "lengthKm": 6.003},
    {"round": 18, "slug": "singapore-2026",  "name": "Singapore Grand Prix",    "country": "Singapore",   "flag": "🇸🇬", "circuit": "Marina Bay Street Circuit",           "date": "2026-10-04T09:00:00Z", "laps": 62, "lengthKm": 5.063},
    {"round": 19, "slug": "usa-2026",        "name": "United States Grand Prix","country": "USA",         "flag": "🇺🇸", "circuit": "Circuit of the Americas",             "date": "2026-10-18T19:00:00Z", "laps": 56, "lengthKm": 5.513},
    {"round": 20, "slug": "mexico-2026",     "name": "Mexico City Grand Prix",  "country": "Mexico",      "flag": "🇲🇽", "circuit": "Autodromo Hermanos Rodriguez",         "date": "2026-10-25T20:00:00Z", "laps": 71, "lengthKm": 4.304},
    {"round": 21, "slug": "brazil-2026",     "name": "Brazilian Grand Prix",    "country": "Brazil",      "flag": "🇧🇷", "circuit": "Autodromo Jose Carlos Pace",          "date": "2026-11-08T17:00:00Z", "laps": 71, "lengthKm": 4.309},
    {"round": 22, "slug": "lasvegas-2026",   "name": "Las Vegas Grand Prix",    "country": "USA",         "flag": "🇺🇸", "circuit": "Las Vegas Street Circuit",            "date": "2026-11-21T06:00:00Z", "laps": 50, "lengthKm": 6.201},
    {"round": 23, "slug": "qatar-2026",      "name": "Qatar Grand Prix",        "country": "Qatar",       "flag": "🇶🇦", "circuit": "Losail International Circuit",        "date": "2026-11-29T14:00:00Z", "laps": 57, "lengthKm": 5.380},
    {"round": 24, "slug": "abudhabi-2026",   "name": "Abu Dhabi Grand Prix",    "country": "UAE",         "flag": "🇦🇪", "circuit": "Yas Marina Circuit",                  "date": "2026-12-06T13:00:00Z", "laps": 58, "lengthKm": 5.281},
]

DRIVER_COLORS = {
    "VER": "#3671C6", "TSU": "#3671C6",
    "NOR": "#FF8000", "PIA": "#FF8000",
    "LEC": "#E8002D", "HAM": "#E8002D",
    "RUS": "#27F4D2", "ANT": "#27F4D2",
    "SAI": "#64C4FF", "ALB": "#64C4FF",
    "ALO": "#229971", "STR": "#229971",
    "HAD": "#6692FF", "LAW": "#6692FF",
    "HUL": "#52E252", "BOR": "#52E252",
    "OCO": "#B6BABD", "BEA": "#B6BABD",
    "GAS": "#FF87BC", "COL": "#FF87BC", "DOO": "#FF87BC",
}

TECH_STACK = ["FastF1", "XGBoost", "Random Forest", "scikit-learn", "FastAPI", "React", "Vite", "Tailwind CSS"]

FEATURE_DETAILS = [
    {"key": "grid_position",       "name": "Grid Position",              "description": "Starting position on the grid. Most predictive single feature."},
    {"key": "avg_finish",          "name": "Avg Finishing Position",     "description": "Driver's average finishing position across 2026 races so far."},
    {"key": "constructor_avg",     "name": "Constructor Avg Finish",     "description": "Team's average finishing position in 2026. Reflects car pace."},
    {"key": "gap_to_pole",         "name": "Gap to Pole (Qualifying)",   "description": "Driver's qualifying time minus pole time. Raw speed indicator."},
    {"key": "avg_pit_time",        "name": "Avg Pit Stop Time",          "description": "Team's average pit stop duration. Faster = competitive advantage."},
    {"key": "avg_pit_stops",       "name": "Avg Pit Stops",              "description": "Average number of pit stops per race. Strategy tendency indicator."},
    {"key": "points",              "name": "Points This Season",         "description": "Total championship points. Captures DNF impact on form."},
    {"key": "lap_consistency",     "name": "Lap Time Consistency",       "description": "Standard deviation of lap times. Lower = more consistent driver."},
    {"key": "dnfs",                "name": "DNFs This Season",           "description": "Number of retirements. Higher = less predictable finishes."},
    {"key": "street_circuit",      "name": "Street Circuit Flag",        "description": "1 if street/semi-permanent circuit, 0 if permanent track."},
    {"key": "weather_wet",         "name": "Weather: Wet Flag",          "description": "1 if wet race, 0 if dry. Wet conditions reshuffle the grid."},
    {"key": "track_temp",          "name": "Track Temperature (°C)",     "description": "Affects tyre degradation and pit strategy."},
]


def fetch_fastf1_data():
    """Fetch live standings and race results from FastF1."""
    completed_rounds = [1, 2, 3, 6]  # Update this as season progresses
    driver_points = {}
    driver_teams = {}
    race_results = {}  # round -> {winner, podium}

    for round_num in completed_rounds:
        try:
            schedule_entry = next((r for r in RACE_SCHEDULE if r["round"] == round_num), None)
            if not schedule_entry:
                continue
            race_name = schedule_entry["name"].replace(" Grand Prix", "").strip()
            session = fastf1.get_session(2026, race_name, "R")
            session.load(laps=False, telemetry=False, weather=False, messages=False)
            results = session.results

            podium_codes = []
            for _, row in results.iterrows():
                code = row.get("Abbreviation", "")
                team = row.get("TeamName", "Unknown")
                pos = row.get("Position", None)
                points = row.get("Points", 0)

                if not code:
                    continue

                driver_teams[code] = team
                driver_points[code] = driver_points.get(code, 0) + float(points or 0)

                if pos and float(pos) <= 3:
                    podium_codes.append((int(float(pos)), code))

            podium_codes.sort(key=lambda x: x[0])
            sorted_podium = [c for _, c in podium_codes]
            race_results[round_num] = {
                "winner": sorted_podium[0] if sorted_podium else None,
                "podium": sorted_podium[:3] if len(sorted_podium) >= 3 else sorted_podium,
            }
        except Exception as e:
            print(f"  Warning: Could not load round {round_num}: {e}")

    return driver_points, driver_teams, race_results


def build_site_data():
    """Build the full site data response."""
    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["data"]

    print("Fetching live data from FastF1...")
    driver_points, driver_teams, race_results = fetch_fastf1_data()

    # ── Build drivers list ────────────────────────────────────────────────────
    seen = set()
    drivers = []
    for code, team in driver_teams.items():
        if code in seen:
            continue
        seen.add(code)
        drivers.append({
            "code": code,
            "name": code,
            "team": team,
            "color": DRIVER_COLORS.get(code, "#888888"),
            "points": int(driver_points.get(code, 0)),
        })
    drivers.sort(key=lambda d: -d["points"])

    # ── Build races list ──────────────────────────────────────────────────────
    from datetime import datetime, timezone
    now_dt = datetime.now(timezone.utc)
    races = []
    next_set = False

    for r in RACE_SCHEDULE:
        race_date = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
        result = race_results.get(r["round"], {})

        MANUALLY_COMPLETED = [1, 2, 3, 6]

        if "status" in r:
            status = r["status"]
        elif r["round"] in MANUALLY_COMPLETED:
            status = "completed"
        elif not next_set and race_date >= now_dt:
            status = "next"
            next_set = True
        else:
            status = "upcoming"

        race_entry = {
            "round": r["round"],
            "slug": r["slug"],
            "name": r["name"],
            "country": r["country"],
            "flag": r["flag"],
            "circuit": r["circuit"],
            "date": r["date"],
            "laps": r["laps"],
            "lengthKm": r["lengthKm"],
            "status": status,
        }
        if result.get("winner"):
            race_entry["winner"] = result["winner"]
        if result.get("podium"):
            race_entry["podium"] = result["podium"]
        if r.get("note"):
            race_entry["note"] = r["note"]

        races.append(race_entry)

    # ── Load predictions from JSON files ─────────────────────────────────────
    predictions_dir = CACHE_DIR.parent / "predictions"
    predictions = []
    print(f"Looking for predictions in: {predictions_dir}")
    print(f"Dir exists: {predictions_dir.exists()}")

    if predictions_dir.exists():
        files = list(predictions_dir.glob("*.json"))
        print(f"Found {len(files)} files: {[f.name for f in files]}")

        for pred_file in sorted(files):
            try:
                print(f"Loading {pred_file.name}...")
                with pred_file.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                print(f"  Keys: {list(raw.keys())}")

                podium = [
                    {
                        "code": p["driver"],
                        "team": p["team"],
                        "confidence": p["confidence"],
                        "pos": p["pos"],
                    }
                    for p in raw.get("predictedPodium", [])
                ]
                print(f"  Podium: {len(podium)} entries")

                grid = [
                    {
                        "code": g["driver"],
                        "team": g["team"],
                        "probability": g["podium_prob"],
                        "predictedPosition": g["position"],
                        "gridPosition": g.get("grid_position", 0),
                        "gridSource": g.get("grid_source", "estimated"),
                    }
                    for g in raw.get("fullGrid", [])
                ]

                raw_importances = raw.get("featureImportances", {})
                max_imp = max(raw_importances.values(), default=1)
                features = [
                    {
                        "key": k,
                        "name": k.replace("_", " ").title(),
                        "weight": round((v / max_imp) * 100, 1),
                        "rawWeight": v,
                    }
                    for k, v in sorted(raw_importances.items(), key=lambda x: -x[1])
                ]

                m = raw.get("metrics", {})
                predictions.append({
                    "slug": raw.get("slug", pred_file.stem),
                    "raceName": raw.get("raceName", ""),
                    "round": raw.get("round", 0),
                    "circuit": raw.get("circuit", ""),
                    "date": raw.get("date", ""),
                    "status": raw.get("status", "Pre-Qualifying Forecast"),
                    "qualifyingDone": raw.get("qualifying_done", False),
                    "modelUsed": raw.get("modelUsed", ""),
                    "podium": podium,
                    "grid": grid,
                    "podiumProb": {g["driver"]: g["podium_prob"] for g in raw.get("fullGrid", [])},
                    "features": features,
                    "metrics": {
                        "f1":        m.get("f1", 0),
                        "precision": m.get("precision", 0),
                        "recall":    m.get("recall", 0),
                        "auc":       m.get("roc_auc", 0),
                    },
                    "trainingData": raw.get("trainingData", {}),
                    "limitations": raw.get("limitations", []),
                    "actualResult": raw.get("actualResult", []),
                })
                print(f"  ✓ Added to predictions")
            except Exception as e:
                print(f"  ERROR loading {pred_file.name}: {e}")
                import traceback
                traceback.print_exc()

    result = {
        "drivers": drivers,
        "races": races,
        "featureDetails": FEATURE_DETAILS,
        "techStack": TECH_STACK,
        "predictions": predictions,
    }

    _cache["data"] = result
    _cache["timestamp"] = time.time()
    return result


@router.get("/site-data")
def get_site_data():
    try:
        return build_site_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))