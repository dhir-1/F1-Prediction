from typing import Literal

from pydantic import BaseModel

RaceStatus = Literal["completed", "cancelled", "next", "upcoming"]


class DriverStanding(BaseModel):
    code: str
    name: str
    team: str
    color: str
    points: int


class Race(BaseModel):
    round: int
    slug: str
    name: str
    country: str
    flag: str
    circuit: str
    date: str
    laps: int
    lengthKm: float
    status: RaceStatus
    winner: str | None = None
    podium: tuple[str, str, str] | None = None
    fastestLap: str | None = None
    note: str | None = None
    winnerImage: str | None = None


class FeatureDetail(BaseModel):
    key: str
    name: str
    description: str


class PredictionPodiumEntry(BaseModel):
    code: str
    team: str
    confidence: float
    pos: int


class PredictionGridEntry(BaseModel):
    code: str
    team: str
    probability: float
    predictedPosition: int
    gridPosition: int
    gridSource: str


class FeatureWeight(BaseModel):
    key: str
    name: str
    weight: int
    rawWeight: float


class PredictionMetrics(BaseModel):
    f1: float
    precision: float
    recall: float
    auc: float


class TrainingData(BaseModel):
    races: list[str]
    rows: int
    cvMethod: str


class RacePrediction(BaseModel):
    slug: str
    raceName: str
    round: int
    circuit: str
    date: str
    status: str
    qualifyingDone: bool
    modelUsed: str
    podium: list[PredictionPodiumEntry]
    grid: list[PredictionGridEntry]
    podiumProb: dict[str, float]
    features: list[FeatureWeight]
    metrics: PredictionMetrics
    trainingData: TrainingData
    limitations: list[str]


class SiteDataResponse(BaseModel):
    drivers: list[DriverStanding]
    races: list[Race]
    featureDetails: list[FeatureDetail]
    techStack: list[str]
    predictions: list[RacePrediction]
