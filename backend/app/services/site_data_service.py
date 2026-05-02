import json
import logging
from pathlib import Path

from app.core.config import PREDICTIONS_DIR, CACHE_DIR
from app.data.season import DRIVERS, FEATURE_DETAILS, FEATURE_LABELS, RACES, TECH_STACK
from app.models.site import RacePrediction, SiteDataResponse

RACES_BY_ROUND = {race["round"]: race for race in RACES}

_FASTF1_CACHE = {}

def _fetch_fastf1_results(year: int, race_name: str):
    cache_key = f"{year}-{race_name}"
    if cache_key in _FASTF1_CACHE:
        return _FASTF1_CACHE[cache_key]

    try:
        import fastf1
        # Enable caching to avoid slow downloads
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))

        session = fastf1.get_session(year, race_name, 'R')
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        
        winner = session.results.iloc[0]["Abbreviation"]
        podium = (
            session.results.iloc[0]["Abbreviation"],
            session.results.iloc[1]["Abbreviation"],
            session.results.iloc[2]["Abbreviation"],
        )
        fastest_lap_row = session.results.sort_values(by="FastestLapTime").iloc[0]
        fastest_lap = fastest_lap_row["Abbreviation"]
        
        _FASTF1_CACHE[cache_key] = {
            "winner": winner,
            "podium": podium,
            "fastestLap": fastest_lap
        }
        return _FASTF1_CACHE[cache_key]
    except Exception as e:
        logging.warning(f"Failed to fetch FastF1 data for {year} {race_name}: {e}")
        _FASTF1_CACHE[cache_key] = None
        return None


def _prediction_files() -> list[Path]:
    if not PREDICTIONS_DIR.exists():
        return []

    return sorted(PREDICTIONS_DIR.glob("*.json"))


def _load_prediction(prediction_path: Path) -> RacePrediction:
    with prediction_path.open("r", encoding="utf-8") as prediction_file:
        raw_prediction = json.load(prediction_file)

    race = RACES_BY_ROUND.get(raw_prediction["round"])
    slug = race["slug"] if race else prediction_path.stem
    max_importance = max(raw_prediction["featureImportances"].values(), default=0.0001)

    podium = [
        {
            "code": item["driver"],
            "team": item["team"],
            "confidence": item["confidence"],
            "pos": item["pos"],
        }
        for item in sorted(raw_prediction["predictedPodium"], key=lambda item: item["pos"])
    ]

    grid = [
        {
            "code": item["driver"],
            "team": item["team"],
            "probability": item["podium_prob"],
            "predictedPosition": item["position"],
            "gridPosition": item["grid_position"],
            "gridSource": item["grid_source"],
        }
        for item in sorted(raw_prediction["fullGrid"], key=lambda item: item["position"])
    ]

    features = [
        {
            "key": key,
            "name": FEATURE_LABELS.get(key, key),
            "weight": round((value / max_importance) * 100),
            "rawWeight": value,
        }
        for key, value in sorted(
            raw_prediction["featureImportances"].items(),
            key=lambda feature: feature[1],
            reverse=True,
        )
    ]

    return RacePrediction.model_validate(
        {
            "slug": slug,
            "raceName": raw_prediction["raceName"],
            "round": raw_prediction["round"],
            "circuit": raw_prediction["circuit"],
            "date": raw_prediction["date"],
            "status": raw_prediction["status"],
            "qualifyingDone": raw_prediction["qualifying_done"],
            "modelUsed": raw_prediction["modelUsed"],
            "podium": podium,
            "grid": grid,
            "podiumProb": {
                item["driver"]: item["podium_prob"] for item in raw_prediction["fullGrid"]
            },
            "features": features,
            "metrics": {
                "f1": raw_prediction["metrics"]["f1"],
                "precision": raw_prediction["metrics"]["precision"],
                "recall": raw_prediction["metrics"]["recall"],
                "auc": raw_prediction["metrics"]["roc_auc"],
            },
            "trainingData": raw_prediction["trainingData"],
            "limitations": raw_prediction["limitations"],
        }
    )


def _load_predictions() -> list[RacePrediction]:
    return sorted(
        (_load_prediction(prediction_path) for prediction_path in _prediction_files()),
        key=lambda prediction: prediction.round,
    )


def get_site_data() -> SiteDataResponse:
    updated_races = []
    for race in RACES:
        race_copy = race.copy()
        if race_copy["status"] == "completed":
            year = int(race_copy["date"].split("-")[0])
            # User wants to fetch real winners from FastF1
            fastf1_data = _fetch_fastf1_results(year, race_copy["name"])
            if fastf1_data:
                race_copy["winner"] = fastf1_data["winner"]
                race_copy["podium"] = fastf1_data["podium"]
                race_copy["fastestLap"] = fastf1_data["fastestLap"]
        updated_races.append(race_copy)

    return SiteDataResponse.model_validate(
        {
            "drivers": DRIVERS,
            "races": updated_races,
            "featureDetails": FEATURE_DETAILS,
            "techStack": TECH_STACK,
            "predictions": [prediction.model_dump() for prediction in _load_predictions()],
        }
    )
