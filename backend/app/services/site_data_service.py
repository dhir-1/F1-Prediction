import json
from pathlib import Path

from app.core.config import PREDICTIONS_DIR
from app.data.season import DRIVERS, FEATURE_DETAILS, FEATURE_LABELS, RACES, TECH_STACK
from app.models.site import RacePrediction, SiteDataResponse

RACES_BY_ROUND = {race["round"]: race for race in RACES}


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
    return SiteDataResponse.model_validate(
        {
            "drivers": DRIVERS,
            "races": RACES,
            "featureDetails": FEATURE_DETAILS,
            "techStack": TECH_STACK,
            "predictions": [prediction.model_dump() for prediction in _load_predictions()],
        }
    )
