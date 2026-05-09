from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import fastf1
from fastapi import APIRouter, HTTPException

from app.core.config import CACHE_DIR

router = APIRouter()

_cache: dict[str, Any] = {"data": None, "timestamp": 0.0}
CACHE_TTL_SECONDS = 300


SEASON_SCHEDULE: list[dict[str, Any]] = [
    {
        "round": 1,
        "slug": "australian-grand-prix",
        "name": "Australian Grand Prix",
        "country": "Australia",
        "flag": "AUS",
        "circuit": "Albert Park Circuit",
        "date": "2026-03-08",
        "laps": 58,
        "lengthKm": 5.278,
    },
    {
        "round": 2,
        "slug": "chinese-grand-prix",
        "name": "Chinese Grand Prix",
        "country": "China",
        "flag": "CHN",
        "circuit": "Shanghai International Circuit",
        "date": "2026-03-15",
        "laps": 56,
        "lengthKm": 5.451,
    },
    {
        "round": 3,
        "slug": "japanese-grand-prix",
        "name": "Japanese Grand Prix",
        "country": "Japan",
        "flag": "JPN",
        "circuit": "Suzuka Circuit",
        "date": "2026-03-29",
        "laps": 53,
        "lengthKm": 5.807,
    },
    {
        "round": 4,
        "slug": "miami-grand-prix",
        "name": "Miami Grand Prix",
        "country": "USA",
        "flag": "US",
        "circuit": "Miami International Autodrome",
        "date": "2026-05-03",
        "laps": 57,
        "lengthKm": 5.412,
    },
    {
        "round": 5,
        "slug": "canadian-grand-prix",
        "name": "Canadian Grand Prix",
        "country": "Canada",
        "flag": "CA",
        "circuit": "Circuit Gilles Villeneuve",
        "date": "2026-05-24",
        "laps": 70,
        "lengthKm": 4.361,
    },
    {
        "round": 6,
        "slug": "monaco-grand-prix",
        "name": "Monaco Grand Prix",
        "country": "Monaco",
        "flag": "MON",
        "circuit": "Circuit de Monaco",
        "date": "2026-06-07",
        "laps": 78,
        "lengthKm": 3.337,
    },
    {
        "round": 7,
        "slug": "barcelona-grand-prix",
        "name": "Barcelona Grand Prix",
        "country": "Spain",
        "flag": "ESP",
        "circuit": "Circuit de Barcelona-Catalunya",
        "date": "2026-06-14",
        "laps": 66,
        "lengthKm": 4.657,
    },
    {
        "round": 8,
        "slug": "austrian-grand-prix",
        "name": "Austrian Grand Prix",
        "country": "Austria",
        "flag": "AUT",
        "circuit": "Red Bull Ring",
        "date": "2026-06-28",
        "laps": 71,
        "lengthKm": 4.318,
    },
    {
        "round": 9,
        "slug": "british-grand-prix",
        "name": "British Grand Prix",
        "country": "United Kingdom",
        "flag": "GBR",
        "circuit": "Silverstone Circuit",
        "date": "2026-07-05",
        "laps": 52,
        "lengthKm": 5.891,
    },
    {
        "round": 10,
        "slug": "belgian-grand-prix",
        "name": "Belgian Grand Prix",
        "country": "Belgium",
        "flag": "BEL",
        "circuit": "Circuit de Spa-Francorchamps",
        "date": "2026-07-19",
        "laps": 44,
        "lengthKm": 7.004,
    },
    {
        "round": 11,
        "slug": "hungarian-grand-prix",
        "name": "Hungarian Grand Prix",
        "country": "Hungary",
        "flag": "HUN",
        "circuit": "Hungaroring",
        "date": "2026-07-26",
        "laps": 70,
        "lengthKm": 4.381,
    },
    {
        "round": 12,
        "slug": "dutch-grand-prix",
        "name": "Dutch Grand Prix",
        "country": "Netherlands",
        "flag": "NED",
        "circuit": "Circuit Zandvoort",
        "date": "2026-08-23",
        "laps": 72,
        "lengthKm": 4.259,
    },
    {
        "round": 13,
        "slug": "italian-grand-prix",
        "name": "Italian Grand Prix",
        "country": "Italy",
        "flag": "ITA",
        "circuit": "Autodromo Nazionale Monza",
        "date": "2026-09-06",
        "laps": 53,
        "lengthKm": 5.793,
    },
    {
        "round": 14,
        "slug": "spanish-grand-prix",
        "name": "Spanish Grand Prix",
        "country": "Spain",
        "flag": "MAD",
        "circuit": "Madring",
        "date": "2026-09-13",
        "laps": 57,
        "lengthKm": 5.470,
    },
    {
        "round": 15,
        "slug": "azerbaijan-grand-prix",
        "name": "Azerbaijan Grand Prix",
        "country": "Azerbaijan",
        "flag": "AZE",
        "circuit": "Baku City Circuit",
        "date": "2026-09-26",
        "laps": 51,
        "lengthKm": 6.003,
    },
    {
        "round": 16,
        "slug": "singapore-grand-prix",
        "name": "Singapore Grand Prix",
        "country": "Singapore",
        "flag": "SIN",
        "circuit": "Marina Bay Street Circuit",
        "date": "2026-10-11",
        "laps": 62,
        "lengthKm": 4.940,
    },
    {
        "round": 17,
        "slug": "united-states-grand-prix",
        "name": "United States Grand Prix",
        "country": "USA",
        "flag": "USA",
        "circuit": "Circuit of The Americas",
        "date": "2026-10-25",
        "laps": 56,
        "lengthKm": 5.513,
    },
    {
        "round": 18,
        "slug": "mexico-city-grand-prix",
        "name": "Mexico City Grand Prix",
        "country": "Mexico",
        "flag": "MEX",
        "circuit": "Autodromo Hermanos Rodriguez",
        "date": "2026-11-01",
        "laps": 71,
        "lengthKm": 4.304,
    },
    {
        "round": 19,
        "slug": "sao-paulo-grand-prix",
        "name": "Sao Paulo Grand Prix",
        "country": "Brazil",
        "flag": "BRA",
        "circuit": "Interlagos",
        "date": "2026-11-08",
        "laps": 71,
        "lengthKm": 4.309,
    },
    {
        "round": 20,
        "slug": "las-vegas-grand-prix",
        "name": "Las Vegas Grand Prix",
        "country": "USA",
        "flag": "LV",
        "circuit": "Las Vegas Strip Circuit",
        "date": "2026-11-21",
        "laps": 50,
        "lengthKm": 6.201,
    },
    {
        "round": 21,
        "slug": "qatar-grand-prix",
        "name": "Qatar Grand Prix",
        "country": "Qatar",
        "flag": "QAT",
        "circuit": "Lusail International Circuit",
        "date": "2026-11-29",
        "laps": 57,
        "lengthKm": 5.419,
    },
    {
        "round": 22,
        "slug": "abu-dhabi-grand-prix",
        "name": "Abu Dhabi Grand Prix",
        "country": "United Arab Emirates",
        "flag": "UAE",
        "circuit": "Yas Marina Circuit",
        "date": "2026-12-06",
        "laps": 58,
        "lengthKm": 5.281,
    },
]

SEASON_BY_ROUND = {race["round"]: race for race in SEASON_SCHEDULE}

DRIVER_FALLBACKS: dict[str, dict[str, str | None]] = {
    "ALB": {"name": "Alexander Albon", "team": "Williams", "number": "23", "headshot": None},
    "ALO": {"name": "Fernando Alonso", "team": "Aston Martin", "number": "14", "headshot": None},
    "ANT": {"name": "Kimi Antonelli", "team": "Mercedes", "number": "12", "headshot": None},
    "BEA": {"name": "Oliver Bearman", "team": "Haas F1 Team", "number": "87", "headshot": None},
    "BOR": {"name": "Gabriel Bortoleto", "team": "Audi", "number": "5", "headshot": None},
    "BOT": {"name": "Valtteri Bottas", "team": "Cadillac", "number": "77", "headshot": None},
    "COL": {"name": "Franco Colapinto", "team": "Alpine", "number": "43", "headshot": None},
    "GAS": {"name": "Pierre Gasly", "team": "Alpine", "number": "10", "headshot": None},
    "HAD": {"name": "Isack Hadjar", "team": "Red Bull Racing", "number": "6", "headshot": None},
    "HAM": {"name": "Lewis Hamilton", "team": "Ferrari", "number": "44", "headshot": None},
    "HUL": {"name": "Nico Hulkenberg", "team": "Audi", "number": "27", "headshot": None},
    "LAW": {"name": "Liam Lawson", "team": "Racing Bulls", "number": "30", "headshot": None},
    "LEC": {"name": "Charles Leclerc", "team": "Ferrari", "number": "16", "headshot": None},
    "LIN": {"name": "Arvid Lindblad", "team": "Racing Bulls", "number": "41", "headshot": None},
    "NOR": {"name": "Lando Norris", "team": "McLaren", "number": "1", "headshot": None},
    "OCO": {"name": "Esteban Ocon", "team": "Haas F1 Team", "number": "31", "headshot": None},
    "PER": {"name": "Sergio Perez", "team": "Cadillac", "number": "11", "headshot": None},
    "PIA": {"name": "Oscar Piastri", "team": "McLaren", "number": "81", "headshot": None},
    "RUS": {"name": "George Russell", "team": "Mercedes", "number": "63", "headshot": None},
    "SAI": {"name": "Carlos Sainz", "team": "Williams", "number": "55", "headshot": None},
    "STR": {"name": "Lance Stroll", "team": "Aston Martin", "number": "18", "headshot": None},
    "VER": {"name": "Max Verstappen", "team": "Red Bull Racing", "number": "3", "headshot": None},
}

FEATURE_DETAILS = [
    {
        "key": "grid_position",
        "name": "Grid Position",
        "description": "Starting place on the grid. It is still the strongest single pre-race signal in Formula One.",
    },
    {
        "key": "avg_finish_last3",
        "name": "Average Finish (Last 3)",
        "description": "Recent finishing form over the last three rounds, used as a compact read on momentum.",
    },
    {
        "key": "constructor_avg_finish",
        "name": "Constructor Average Finish",
        "description": "Average finishing strength of the team, which acts as a proxy for the car underneath the driver.",
    },
    {
        "key": "gap_to_pole",
        "name": "Gap To Pole",
        "description": "Qualifying gap to the fastest lap. Useful as a speed signal when the race pace picture is still noisy.",
    },
    {
        "key": "avg_pit_time",
        "name": "Average Pit Time",
        "description": "Average stationary pit time for the team, capturing execution quality under pressure.",
    },
    {
        "key": "avg_pit_count",
        "name": "Average Pit Count",
        "description": "Typical number of pit stops, which gives the model a hint about strategic style and tyre management.",
    },
    {
        "key": "season_points",
        "name": "Season Points",
        "description": "Total points scored so far in the season, mixing pace, consistency, and reliability into one number.",
    },
    {
        "key": "lap_consistency_std",
        "name": "Lap Consistency",
        "description": "Standard deviation of representative lap times. Lower spread usually means steadier race execution.",
    },
    {
        "key": "dnf_count",
        "name": "DNF Count",
        "description": "Number of retirements so far, included as a lightweight reliability signal.",
    },
    {
        "key": "street_circuit",
        "name": "Street Circuit Flag",
        "description": "Binary track-type flag to tell the model when walls, safety cars, and track evolution matter more.",
    },
    {
        "key": "weather_wet",
        "name": "Wet Weather Flag",
        "description": "Marks wet conditions, which can scramble the normal pecking order faster than almost any other factor.",
    },
    {
        "key": "track_temp",
        "name": "Track Temperature",
        "description": "Track temperature in Celsius, included because tyre behaviour and degradation shift with heat.",
    },
    {
        "key": "new_regs",
        "name": "New Regulations",
        "description": "Flags weekends affected by the 2026 regulation reset so the model can at least acknowledge the regime change.",
    },
]

FEATURE_NAME_BY_KEY = {feature["key"]: feature["name"] for feature in FEATURE_DETAILS}

TECH_STACK = [
    "FastF1",
    "Python 3.11",
    "XGBoost",
    "Random Forest",
    "FastAPI",
    "React 19",
    "Vite",
    "Tailwind CSS",
    "TanStack Router",
]


def _configure_fastf1() -> None:
    fastf1.Cache.enable_cache(str(CACHE_DIR))
    fastf1.Cache.offline_mode(True)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        if value != value:
            return None
        return str(value)
    text = str(value).strip()
    return text or None


def _team_color(value: Any) -> str:
    color = _clean_text(value)
    if not color:
        return "#888888"
    return color if color.startswith("#") else f"#{color}"


def _prediction_result_summary(prediction: dict[str, Any]) -> dict[str, Any] | None:
    actual = prediction.get("actualResult") or []
    if not actual:
        return None
    ordered = sorted(actual, key=lambda item: int(item.get("pos", 999)))
    podium = [item.get("driver", "").strip().upper() for item in ordered[:3] if item.get("driver")]
    if not podium:
        return None
    return {"winner": podium[0], "podium": podium}


def _load_predictions() -> list[dict[str, Any]]:
    predictions_dir = CACHE_DIR.parent / "predictions"
    predictions: list[dict[str, Any]] = []

    if not predictions_dir.exists():
        return predictions

    for path in sorted(predictions_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        feature_keys = raw.get("features") or []
        importances = raw.get("featureImportances") or {}
        total_importance = sum(float(importances.get(key, 0.0)) for key in feature_keys) or 1.0

        features = [
            {
                "key": key,
                "name": FEATURE_NAME_BY_KEY.get(key, key.replace("_", " ").title()),
                "weight": round((float(importances.get(key, 0.0)) / total_importance) * 100, 1),
                "rawWeight": round(float(importances.get(key, 0.0)), 4),
            }
            for key in feature_keys
        ]

        podium = []
        podium_prob: dict[str, float] = {}
        for entry in raw.get("predictedPodium", []):
            code = str(entry.get("driver", "")).strip().upper()
            confidence = float(entry.get("confidence", 0.0))
            podium_prob[code] = confidence
            podium.append(
                {
                    "code": code,
                    "team": entry.get("team", "Unknown"),
                    "confidence": confidence,
                    "pos": int(entry.get("pos", len(podium) + 1)),
                }
            )

        grid = [
            {
                "code": str(entry.get("driver", "")).strip().upper(),
                "team": entry.get("team", "Unknown"),
                "probability": float(entry.get("podium_prob", 0.0)),
                "predictedPosition": int(entry.get("position", 0)),
                "gridPosition": int(entry.get("grid_position", 0)),
                "gridSource": entry.get("grid_source", "Estimated grid"),
            }
            for entry in raw.get("fullGrid", [])
        ]

        metrics = raw.get("metrics") or {}
        predictions.append(
            {
                "slug": raw.get("slug", path.stem),
                "raceName": raw.get("raceName", path.stem.replace("-", " ").title()),
                "round": int(raw.get("round", 0)),
                "circuit": raw.get("circuit", ""),
                "date": raw.get("date", ""),
                "status": raw.get("status", "Draft"),
                "qualifyingDone": bool(raw.get("qualifying_done", raw.get("qualifyingDone", False))),
                "modelUsed": raw.get("modelUsed", "Unknown"),
                "podium": podium,
                "grid": grid,
                "podiumProb": podium_prob,
                "features": features,
                "metrics": {
                    "f1": float(metrics.get("f1", 0.0)),
                    "precision": float(metrics.get("precision", 0.0)),
                    "recall": float(metrics.get("recall", 0.0)),
                    "auc": float(metrics.get("roc_auc", metrics.get("auc", 0.0))),
                },
                "trainingData": raw.get("trainingData", {"races": [], "rows": 0, "cvMethod": "Unknown"}),
                "limitations": raw.get("limitations", []),
                "actualResult": raw.get("actualResult", []),
                "pitWallNotes": raw.get("pitWallNotes", []),
            }
        )

    predictions.sort(key=lambda item: item["round"])
    return predictions


def _load_live_results() -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, float]]:
    today = date.today()
    completed_results: dict[int, dict[str, Any]] = {}
    driver_identity: dict[str, dict[str, Any]] = {}
    driver_points: defaultdict[str, float] = defaultdict(float)

    for race in SEASON_SCHEDULE:
        race_date = date.fromisoformat(race["date"])
        if race_date > today:
            continue

        try:
            session = fastf1.get_session(2026, race["round"], "R")
            session.load(laps=False, telemetry=False, weather=False, messages=False)
        except Exception:
            continue

        results = session.results
        if results is None or results.empty:
            continue

        ordered = results.sort_values("Position")
        podium = []

        for _, row in ordered.iterrows():
            code = str(row.get("Abbreviation", "")).strip().upper()
            if not code:
                continue

            if len(podium) < 3:
                podium.append(code)

            team = _clean_text(row.get("TeamName")) or DRIVER_FALLBACKS.get(code, {}).get("team") or "Unknown"
            driver_identity[code] = {
                "code": code,
                "name": _clean_text(row.get("FullName")) or DRIVER_FALLBACKS.get(code, {}).get("name") or code,
                "team": team,
                "color": _team_color(row.get("TeamColor")),
                "number": _clean_text(row.get("DriverNumber")) or DRIVER_FALLBACKS.get(code, {}).get("number"),
                "headshot": _clean_text(row.get("HeadshotUrl")) or DRIVER_FALLBACKS.get(code, {}).get("headshot"),
                "broadcastName": _clean_text(row.get("BroadcastName")),
            }
            driver_points[code] += float(row.get("Points", 0.0) or 0.0)

        if podium:
            completed_results[race["round"]] = {
                "winner": podium[0],
                "podium": podium[:3],
            }

    for code, fallback in DRIVER_FALLBACKS.items():
        driver_identity.setdefault(
            code,
            {
                "code": code,
                "name": fallback["name"] or code,
                "team": fallback["team"] or "Unknown",
                "color": "#888888",
                "number": fallback["number"],
                "headshot": fallback["headshot"],
                "broadcastName": None,
            },
        )
        driver_points.setdefault(code, 0.0)

    return completed_results, driver_identity, dict(driver_points)


def _build_races(predictions: list[dict[str, Any]], live_results: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    today = date.today()
    next_round = None

    for race in SEASON_SCHEDULE:
        if date.fromisoformat(race["date"]) >= today:
            next_round = race["round"]
            break

    prediction_results = {
        prediction["round"]: summary
        for prediction in predictions
        if (summary := _prediction_result_summary(prediction)) is not None
    }

    races = []
    for race in SEASON_SCHEDULE:
        result = live_results.get(race["round"]) or prediction_results.get(race["round"])
        status = "completed" if result else "upcoming"
        if not result and race["round"] == next_round:
            status = "next"

        races.append(
            {
                **race,
                "status": status,
                "winner": result["winner"] if result else None,
                "podium": result["podium"] if result else None,
                "fastestLap": None,
                "note": None,
                "winnerImage": f"/images/winners/{race['slug']}.jpg" if result else None,
            }
        )

    return races


def build_site_data() -> dict[str, Any]:
    _configure_fastf1()
    predictions = _load_predictions()
    live_results, driver_identity, driver_points = _load_live_results()
    races = _build_races(predictions, live_results)

    drivers = []
    for code, identity in driver_identity.items():
        drivers.append(
            {
                "code": code,
                "name": identity["name"],
                "team": identity["team"],
                "color": identity["color"],
                "points": round(float(driver_points.get(code, 0.0)), 1),
                "number": identity.get("number"),
                "headshot": identity.get("headshot"),
                "broadcastName": identity.get("broadcastName"),
            }
        )

    drivers.sort(key=lambda driver: (-driver["points"], driver["name"]))

    return {
        "drivers": drivers,
        "races": races,
        "featureDetails": FEATURE_DETAILS,
        "techStack": TECH_STACK,
        "predictions": predictions,
    }


@router.get("/site-data")
def get_site_data() -> dict[str, Any]:
    now = time.time()
    cached = _cache.get("data")
    if cached is not None and now - float(_cache.get("timestamp", 0.0)) < CACHE_TTL_SECONDS:
        return cached

    try:
        data = build_site_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build site data: {exc}") from exc

    _cache["data"] = data
    _cache["timestamp"] = now
    return data
