"""
monaco_prediction.py — Dhir's Pit Wall · Round 6 · Monaco GP · June 8, 2026
=============================================================================
Training data : 5 completed 2026 races (Australia, China, Japan, Miami, Canada)
Features      : grid_position, avg_grid_position, avg_finish_last3, finish_trend,
                points_per_race, avg_lap_time_delta (Q3 quali), constructor_avg_finish,
                dnf_count, monaco_grid_penalty (grid_position^2)
Models        : SoftVotingClassifier — XGBClassifier + XGBRegressorClassifier + LGBMClassifier
                + CalibratedClassifierCV (sigmoid, prefit) to fix overconfidence
Tuning        : Optuna only, 5-fold CV, f1 scoring
Data          : FastF1 for all lap times, results, Monaco Q3

WORKFLOW
--------
  Before qualifying : USE_GRID_POSITION=False, QUALIFYING_DONE=False
  After qualifying  : USE_GRID_POSITION=True,  QUALIFYING_DONE=True
  After race        : fill actualResult in JSON
"""

import json
import warnings
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd
import optuna
from optuna.samplers import TPESampler
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier, XGBRegressor

optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")


# =============================================================================
# SECTION 0 — SETTINGS
# =============================================================================

QUALIFYING_DONE   = True
USE_GRID_POSITION = True

ROUND_NUMBER = 6
RACE_NAME    = "Monaco Grand Prix"
CIRCUIT      = "Circuit de Monaco"
RACE_DATE    = "2026-06-08"

SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
CACHE_DIR   = BACKEND_DIR / "data" / "fastf1_cache"
OUTPUT_FILE = BACKEND_DIR / "data" / "predictions" / "monaco-2026.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

TRAINING_RACES = [
    (2026, "Australia", "R"),
    (2026, "China",     "R"),
    (2026, "Japan",     "R"),
    (2026, "Miami",     "R"),
    (2026, "Canada",    "R"),
]

MONACO_QUALIFYING_GRID = {
    "ANT": 1,
    "VER": 2,
    "HAM": 3,
    "LEC": 4,
    "HAD": 5,
    "RUS": 6,
    "PIA": 7,
    "NOR": 8,
    "GAS": 9,
    "LAW": 10,
    "ALB": 11,
    "SAI": 12,
    "HUL": 13,
    "COL": 14,
    "LIN": 15,
    "BOR": 16,
    "OCO": 17,
    "PER": 18,
    "BEA": 19,
    "BOT": 20,
    "ALO": 21,
    "STR": 22,
}

MAX_POINTS_PER_RACE = 25
TOTAL_RACES         = len(TRAINING_RACES)
MAX_POSSIBLE_POINTS = MAX_POINTS_PER_RACE * TOTAL_RACES  # 125

CV_FOLDS    = 5
CV_SCORING  = "f1"
N_OPTUNA    = 50
RANDOM_SEED = 42


# =============================================================================
# SECTION 1 — FEATURE COLUMNS
# =============================================================================

_ALL_FEATURES = [
    "grid_position",          # only when USE_GRID_POSITION=True
    "monaco_grid_penalty",    # grid_position^2 — exponential street circuit penalty
    "avg_grid_position",
    "avg_finish_last3",
    "finish_trend",
    "points_per_race",
    "avg_lap_time_delta",     # Q3 quali delta for inference, race lap delta for training
    "constructor_avg_finish",
    "dnf_count",
]

def get_feature_cols() -> list:
    # monaco_grid_penalty only meaningful when grid_position is included
    excluded = []
    if not USE_GRID_POSITION:
        excluded += ["grid_position", "monaco_grid_penalty"]
    return [f for f in _ALL_FEATURES if f not in excluded]


# =============================================================================
# SECTION 2 — LOAD SESSIONS
# =============================================================================

def load_sessions() -> list:
    print(f"\n[1/6] Loading {len(TRAINING_RACES)} race sessions via FastF1...")
    sessions = []
    for year, race, stype in TRAINING_RACES:
        print(f"  → {year} {race}...", end=" ", flush=True)
        sess = fastf1.get_session(year, race, stype)
        sess.load(laps=True, telemetry=False, weather=False, messages=False)
        sessions.append(sess)
        print(f"✓ {len(sess.results)} drivers")
    print(f"  ✓ All sessions loaded")
    return sessions


def load_monaco_quali_delta() -> dict:
    """
    Load Monaco qualifying lap time delta vs pole (Q3 → Q2 → Q1 fallback).
    Q3 = max attack, empty tanks, true car pace — best signal for Monaco.
    Returns dict: driver_code → delta in seconds vs pole time.
    """
    print("\n[1b/6] Loading Monaco qualifying lap time deltas...")
    quali_deltas = {}
    try:
        q_sess = fastf1.get_session(2026, ROUND_NUMBER, "Q")
        q_sess.load(laps=True, telemetry=False, weather=False, messages=False)

        results = q_sess.results

        # Find pole time — best Q3 time across all drivers
        pole_time = None
        for _, row in results.iterrows():
            for q in ["Q3", "Q2", "Q1"]:
                t = row.get(q)
                if t is not None and pd.notna(t):
                    t_sec = t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                    if pole_time is None or t_sec < pole_time:
                        pole_time = t_sec
                    break  # only use best available for pole calc

        # Actually use Q3 minimum as pole
        q3_times = []
        for _, row in results.iterrows():
            t = row.get("Q3")
            if t is not None and pd.notna(t):
                t_sec = t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                q3_times.append(t_sec)
        if q3_times:
            pole_time = min(q3_times)

        if pole_time is None:
            print("  ⚠️ Could not determine pole time — falling back to season avg")
            return {}

        # Delta per driver: Q3 → Q2 → Q1 fallback
        for _, row in results.iterrows():
            code = str(row.get("Abbreviation", "")).strip().upper()
            if not code:
                continue
            drv_time = None
            for q in ["Q3", "Q2", "Q1"]:
                t = row.get(q)
                if t is not None and pd.notna(t):
                    drv_time = t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                    break
            if drv_time is not None:
                quali_deltas[code] = round(drv_time - pole_time, 3)

        print(f"  ✓ Qualifying deltas loaded for {len(quali_deltas)} drivers")
        print(f"  ✓ Pole time: {pole_time:.3f}s")

    except Exception as exc:
        print(f"  ⚠️ Qualifying load failed ({exc}) — falling back to season avg")

    return quali_deltas


# =============================================================================
# SECTION 3 — COMPUTE PER-RACE FEATURES
# =============================================================================

def compute_race_features(sessions: list) -> pd.DataFrame:
    print("\n[2/6] Computing per-race features from FastF1...")
    all_rows = []

    for sess_idx, sess in enumerate(sessions):
        results   = sess.results
        laps      = sess.laps
        race_name = sess.event["EventName"]

        # Winner avg lap time — baseline for race lap delta
        winner_code    = results.sort_values("Position").iloc[0]["Abbreviation"]
        winner_laps    = laps.pick_drivers(winner_code).pick_quicklaps()
        winner_avg_lap = (
            winner_laps["LapTime"].dropna()
                        .apply(lambda t: t.total_seconds())
                        .mean()
            if not winner_laps.empty else None
        )

        for _, driver in results.iterrows():
            code       = str(driver["Abbreviation"]).strip().upper()
            finish_pos = float(driver.get("Position",     20) or 20)
            grid_pos   = float(driver.get("GridPosition", 11) or 11)
            points     = float(driver.get("Points",        0) or  0)
            team       = str(driver.get("TeamName", "Unknown"))
            status     = str(driver.get("Status", ""))

            is_dnf = 1 if (
                status not in ("Finished",)
                and "Lap" not in status
                and "+" not in status
            ) else 0

            # avg_lap_time_delta vs race winner
            drv_laps   = laps.pick_drivers(code)
            clean_laps = drv_laps.pick_quicklaps()
            if not clean_laps.empty and winner_avg_lap:
                drv_avg = (
                    clean_laps["LapTime"].dropna()
                               .apply(lambda t: t.total_seconds())
                               .mean()
                )
                avg_lap_time_delta = drv_avg - winner_avg_lap
            else:
                avg_lap_time_delta = 2.0

            all_rows.append({
                "driver":             code,
                "team":               team,
                "race":               race_name,
                "sess_idx":           sess_idx,
                "finish_position":    finish_pos,
                "grid_position":      grid_pos,
                "points":             points,
                "is_dnf":             is_dnf,
                "avg_lap_time_delta": avg_lap_time_delta,
                "podium":             1 if finish_pos <= 3 else 0,
            })

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)
    print(f"  ✓ {len(df)} rows across {df['race'].nunique()} races")
    return df


# =============================================================================
# SECTION 4 — ROLLING & SEASON FEATURES
# =============================================================================

def compute_trend(series: pd.Series) -> pd.Series:
    vals   = series.values
    trends = [0.0]
    for i in range(1, len(vals)):
        window = vals[max(0, i - 3):i + 1]
        if len(window) >= 2:
            slope = np.polyfit(np.arange(len(window)), window, 1)[0]
            trends.append(float(slope))
        else:
            trends.append(0.0)
    return pd.Series(trends, index=series.index)


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[3/6] Adding rolling features...")
    df = df.copy()

    # avg_finish_last3
    df["avg_finish_last3"] = (
        df.groupby("driver")["finish_position"]
          .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # finish_trend
    df["finish_trend"] = (
        df.groupby("driver")["finish_position"]
          .transform(compute_trend)
    )

    # points_per_race
    df["cumulative_points"] = df.groupby("driver")["points"].cumsum()
    df["race_number"]       = df.groupby("driver").cumcount() + 1
    df["points_per_race"]   = df["cumulative_points"] / df["race_number"]

    # constructor_avg_finish — FIXED: rolling season average per constructor
    df = df.sort_values(["team", "sess_idx"]).reset_index(drop=True)
    df["constructor_avg_finish"] = (
        df.groupby("team")["finish_position"]
          .transform(lambda x: x.expanding().mean())
    )
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)

    # avg_grid_position — season expanding mean
    df["avg_grid_position"] = (
        df.groupby("driver")["grid_position"]
          .transform(lambda x: x.expanding().mean())
    )

    # dnf_count — cumulative
    df["dnf_count"] = (
        df.groupby("driver")["is_dnf"]
          .transform(lambda x: x.cumsum())
    )

    # monaco_grid_penalty — grid_position^2 for training rows
    # Uses actual race grid position squared
    df["monaco_grid_penalty"] = df["grid_position"] ** 2

    print(f"  ✓ Podium distribution: {df['podium'].value_counts().to_dict()}")
    print(f"  ✓ DNF distribution: {df['is_dnf'].value_counts().to_dict()}")
    return df


# =============================================================================
# SECTION 5 — XGBRegressorClassifier WRAPPER
# =============================================================================

class XGBRegressorClassifier(ClassifierMixin, BaseEstimator):
    """
    Wraps XGBRegressor for use inside sklearn VotingClassifier.
    Predicts finish position proxy, converts to podium probability.
    """
    _estimator_type = "classifier"

    def __init__(self, n_estimators=100, max_depth=3,
                 learning_rate=0.05, subsample=0.8,
                 colsample_bytree=0.8, random_state=42):
        self.n_estimators     = n_estimators
        self.max_depth        = max_depth
        self.learning_rate    = learning_rate
        self.subsample        = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state     = random_state
        self.classes_         = np.array([0, 1])

    def fit(self, X, y):
        y_reg = np.where(y == 1, 2.0, 12.0)
        self._model = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            verbosity=0,
            random_state=self.random_state,
        )
        self._model.fit(X, y_reg)
        return self

    def predict_proba(self, X):
        pred_pos    = self._model.predict(X)
        prob_podium = np.clip(1.0 - (pred_pos / 22.0), 0.0, 1.0)
        return np.column_stack([1.0 - prob_podium, prob_podium])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


# =============================================================================
# SECTION 6 — OPTUNA TUNING
# =============================================================================

def tune_optuna(X: np.ndarray, y: np.ndarray) -> tuple:
    """Optuna for all 3 models. Returns (xgb_clf, xgb_reg, lgbm_clf, op_scores)."""
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    spw   = n_neg / n_pos if n_pos > 0 else 1.0
    cv    = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def _cv_score(model):
        scores = []
        for tr, val in cv.split(X, y):
            model.fit(X[tr], y[tr])
            scores.append(f1_score(y[val], model.predict(X[val]), zero_division=0))
        return float(np.mean(scores))

    print("\n  Optuna — XGBClassifier...")
    def xgb_obj(trial):
        m = XGBClassifier(
            n_estimators=    trial.suggest_int("n_estimators", 50, 200),
            max_depth=       trial.suggest_int("max_depth", 2, 3),      # capped at 3
            learning_rate=   trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample=       trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 0.9),  # floor 0.7
            reg_lambda=      trial.suggest_float("reg_lambda", 3.0, 10.0),
            scale_pos_weight=spw,
            use_label_encoder=False, eval_metric="logloss",
            verbosity=0, random_state=RANDOM_SEED,
        )
        return _cv_score(m)
    xgb_study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    xgb_study.optimize(xgb_obj, n_trials=N_OPTUNA)
    best_xgb_op = XGBClassifier(
        **xgb_study.best_params,
        scale_pos_weight=spw,
        use_label_encoder=False, eval_metric="logloss",
        verbosity=0, random_state=RANDOM_SEED,
    )
    best_xgb_op.fit(X, y)
    print(f"    Best CV f1={xgb_study.best_value:.4f}")

    print("  Optuna — XGBRegressorClassifier...")
    def reg_obj(trial):
        m = XGBRegressorClassifier(
            n_estimators= trial.suggest_int("n_estimators", 50, 200),
            max_depth=    trial.suggest_int("max_depth", 2, 3),         # capped at 3
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample=    trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),  # floor 0.7
            random_state= RANDOM_SEED,
        )
        return _cv_score(m)
    reg_study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    reg_study.optimize(reg_obj, n_trials=N_OPTUNA)
    best_reg_op = XGBRegressorClassifier(**reg_study.best_params, random_state=RANDOM_SEED)
    best_reg_op.fit(X, y)
    print(f"    Best CV f1={reg_study.best_value:.4f}")

    print("  Optuna — LGBMClassifier...")
    def lgbm_obj(trial):
        m = LGBMClassifier(
            n_estimators= trial.suggest_int("n_estimators", 50, 200),
            max_depth=    trial.suggest_int("max_depth", 2, 3),         # capped at 3
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            num_leaves=   trial.suggest_int("num_leaves", 7, 31),       # lower = shallower
            subsample=    trial.suggest_float("subsample", 0.6, 1.0),
            reg_lambda=   trial.suggest_float("reg_lambda", 0.5, 10.0),
            class_weight="balanced", random_state=RANDOM_SEED, verbose=-1,
        )
        return _cv_score(m)
    lgbm_study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    lgbm_study.optimize(lgbm_obj, n_trials=N_OPTUNA)
    best_lgbm_op = LGBMClassifier(
        **lgbm_study.best_params,
        class_weight="balanced", random_state=RANDOM_SEED, verbose=-1,
    )
    best_lgbm_op.fit(X, y)
    print(f"    Best CV f1={lgbm_study.best_value:.4f}")

    op_scores = {
        "XGBClassifier":          round(xgb_study.best_value, 4),
        "XGBRegressorClassifier": round(reg_study.best_value, 4),
        "LGBMClassifier":         round(lgbm_study.best_value, 4),
    }

    return best_xgb_op, best_reg_op, best_lgbm_op, op_scores


# =============================================================================
# SECTION 7 — BUILD MONACO INFERENCE ROWS
# =============================================================================

def build_monaco_rows(df: pd.DataFrame, sessions: list, quali_deltas: dict) -> pd.DataFrame:
    """
    One row per driver using full 2026 history.
    avg_lap_time_delta = Monaco Q3 delta if available, else season avg.
    monaco_grid_penalty = grid_position^2.
    """
    last_results = sessions[-1].results
    feature_cols = get_feature_cols()
    rows = []

    for _, driver in last_results.iterrows():
        code = str(driver["Abbreviation"]).strip().upper()
        team = str(driver.get("TeamName", "Unknown"))

        drv_history = df[df["driver"] == code].sort_values("sess_idx")

        if drv_history.empty:
            row = {feat: 0.0 for feat in feature_cols}
            row.update({"driver": code, "team": team})
            rows.append(row)
            continue

        last = drv_history.iloc[-1]

        # grid_position for Monaco
        if USE_GRID_POSITION and QUALIFYING_DONE:
            grid_pos = float(MONACO_QUALIFYING_GRID.get(code, last["avg_grid_position"]))
        else:
            grid_pos = float(last["avg_grid_position"])

        # avg_lap_time_delta — Q3 Monaco specific, fallback to season avg
        lap_delta = quali_deltas.get(
            code,
            float(drv_history["avg_lap_time_delta"].mean())
        )

        row = {
            "driver":                 code,
            "team":                   team,
            "grid_position":          grid_pos,
            "monaco_grid_penalty":    grid_pos ** 2,
            "avg_grid_position":      float(last["avg_grid_position"]),
            "avg_finish_last3":       float(last["avg_finish_last3"]),
            "finish_trend":           float(last["finish_trend"]),
            "points_per_race":        float(last["points_per_race"]),
            "avg_lap_time_delta":     lap_delta,
            "constructor_avg_finish": float(last["constructor_avg_finish"]),
            "dnf_count":              float(last["dnf_count"]),
        }
        rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 8 — PREDICT & RANK
# =============================================================================

def predict_monaco(voting_clf, best_xgb_cls, monaco_df: pd.DataFrame,
                   X_train: np.ndarray, y_train: np.ndarray) -> tuple:
    feature_cols = get_feature_cols()
    X_monaco     = monaco_df[feature_cols].fillna(0).values

    # Calibrate the voting ensemble to fix overconfidence
    print("  Calibrating ensemble (sigmoid, prefit)...")
    calibrated = CalibratedClassifierCV(estimator=voting_clf, method="sigmoid", cv=None)
    calibrated.fit(X_train, y_train)

    probs                     = calibrated.predict_proba(X_monaco)[:, 1]
    monaco_df                 = monaco_df.copy()
    monaco_df["podium_prob"]  = probs
    monaco_df                 = monaco_df.sort_values("podium_prob", ascending=False).reset_index(drop=True)
    monaco_df["predicted_pos"] = monaco_df.index + 1

    # Feature importances from raw XGBClassifier (before calibration)
    importances = {}
    if hasattr(best_xgb_cls, "feature_importances_"):
        total = best_xgb_cls.feature_importances_.sum()
        for feat, imp in zip(feature_cols, best_xgb_cls.feature_importances_):
            importances[feat] = round(float(imp / total) * 100, 1)

    full_grid = [
        {
            "position":    int(row["predicted_pos"]),
            "driver":      row["driver"],
            "team":        row["team"],
            "podiumProb":  round(float(row["podium_prob"]) * 100, 1),
            "gridPosition": int(MONACO_QUALIFYING_GRID.get(row["driver"], 0)) if QUALIFYING_DONE else None,
        }
        for _, row in monaco_df.iterrows()
    ]

    return full_grid, importances


# =============================================================================
# SECTION 9 — SAVE JSON
# =============================================================================

def save_json(full_grid, importances, feature_cols, tuning_summary, quali_used: bool) -> None:
    podium   = full_grid[:3]
    status   = "Final Prediction" if QUALIFYING_DONE else "Pre-Qualifying Forecast"
    grid_imp = importances.get("grid_position", 0)
    pen_imp  = importances.get("monaco_grid_penalty", 0)

    output = {
        "slug":     "monaco-grand-prix",
        "raceName": RACE_NAME,
        "round":    ROUND_NUMBER,
        "circuit":  CIRCUIT,
        "date":     RACE_DATE,
        "status":   status,
        "qualifyingDone": QUALIFYING_DONE,

        "modelUsed": "CalibratedClassifierCV → VotingClassifier (XGBClassifier · XGBRegressorClassifier · LGBMClassifier)",

        "predictedPodium": [
            {
                "pos":        p["position"],
                "driver":     p["driver"],
                "team":       p["team"],
                "confidence": p["podiumProb"],
            }
            for p in podium
        ],
        "fullGrid": full_grid,

        "features":           feature_cols,
        "featureImportances": importances,

        "modelMetrics": {
            "cvFolds":     CV_FOLDS,
            "cvScoring":   CV_SCORING,
            "calibration": "CalibratedClassifierCV sigmoid cv=None",
            "tuning":      tuning_summary,
        },

        "trainingData": {
            "races":    ["Australia", "China", "Japan", "Miami", "Canada"],
            "rows":     TOTAL_RACES * 22,
            "cvMethod": "Optuna · 5-fold · f1",
        },

        "actualResult": {
            "P1": "ANT",
            "P2": "HAM",
            "P3": "HAD",
        },

        "pitWallNotes": [
            "Monaco 2026: Active aero disabled by FIA — mechanical grip only.",
            "Boost Button is the primary overtake mechanism: Portier → Nouvelle Chicane.",
            "Electric power capped at 200km/h through the tunnel.",
            "Cars 10cm narrower in 2026 regs — slightly more room but overtaking still rare.",
            "dnf_count critical — Monaco walls + Boost Button aggression = high DNF risk.",
            "Leclerc hit the wall on his final Q3 lap — car damage risk for Sunday.",
            f"avg_lap_time_delta source: {'Monaco Q3 qualifying ✓' if quali_used else 'season average (Q3 unavailable)'}.",
            f"monaco_grid_penalty (grid^2) importance: {pen_imp:.1f}% — exponential street circuit dropoff.",
            f"grid_position importance: {grid_imp:.1f}%  |  combined grid signal: {grid_imp + pen_imp:.1f}%.",
            f"Calibration applied: sigmoid cv=None — probabilities smoothed from raw tree overconfidence.",
            f"Tuning: Optuna · XGB={tuning_summary['XGBClassifier']['optuna_f1']:.4f}, "
            f"XGBReg={tuning_summary['XGBRegressorClassifier']['optuna_f1']:.4f}, "
            f"LGBM={tuning_summary['LGBMClassifier']['optuna_f1']:.4f}.",
        ],

        "limitations": [
            "110 training rows — midfield probabilities will compress toward similar values.",
            "dnf_count from 5 races only — small sample.",
            "FastF1 data for 2026 may be incomplete for newer teams (Cadillac, RB).",
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n  ✓ Saved → {OUTPUT_FILE}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    feature_cols = get_feature_cols()
    print("=" * 65)
    print(f"  DHIR'S PIT WALL — {RACE_NAME.upper()} 2026")
    print(f"  Round {ROUND_NUMBER} · {CIRCUIT} · {RACE_DATE}")
    print(f"  Features: {len(feature_cols)} | USE_GRID_POSITION={USE_GRID_POSITION}")
    print("=" * 65)

    # 1. Load race sessions + Monaco qualifying deltas
    sessions     = load_sessions()
    quali_deltas = load_monaco_quali_delta()
    quali_used   = len(quali_deltas) > 0

    # 2. Per-race features from FastF1
    race_df = compute_race_features(sessions)

    # 3. Rolling features
    race_df = add_rolling_features(race_df)

    # 4. Tune
    print(f"\n[4/6] Tuning — Optuna ({CV_FOLDS}-fold, {CV_SCORING})")
    X_train = race_df[feature_cols].fillna(0).values
    y_train = race_df["podium"].values

    print("\n── Optuna ──────────────────────────────────────────────────────")
    best_xgb, best_reg, best_lgbm, op_scores = tune_optuna(X_train, y_train)

    tuning_summary = {
        "XGBClassifier":          {"optuna_f1": op_scores["XGBClassifier"]},
        "XGBRegressorClassifier": {"optuna_f1": op_scores["XGBRegressorClassifier"]},
        "LGBMClassifier":         {"optuna_f1": op_scores["LGBMClassifier"]},
    }

    # 5. Build ensemble
    print("\n[5/6] Building VotingClassifier (soft) + Calibration...")
    voting_clf = VotingClassifier(
        estimators=[("xgb", best_xgb), ("xgb_reg", best_reg), ("lgbm", best_lgbm)],
        voting="soft",
    )
    voting_clf.fit(X_train, y_train)
    print("  ✓ Ensemble: XGBClassifier + XGBRegressorClassifier + LGBMClassifier")

    # 6. Predict with calibration
    print(f"\n[6/6] Predicting Monaco ({'POST-QUALIFYING' if QUALIFYING_DONE else 'PRE-QUALIFYING'})...")
    monaco_df = build_monaco_rows(race_df, sessions, quali_deltas)
    full_grid, importances = predict_monaco(voting_clf, best_xgb, monaco_df, X_train, y_train)

    # Print results
    print("\n" + "=" * 65)
    print(f"  🏁  MONACO GP 2026 — {'FINAL' if QUALIFYING_DONE else 'PRE-QUALIFYING'}")
    print("=" * 65)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for entry in full_grid[:3]:
        print(f"  {medals[entry['position']]}  P{entry['position']}  {entry['driver']:<6}  {entry['team']:<25}  {entry['podiumProb']}%")

    print(f"\n  avg_lap_time_delta source: {'Monaco Q3 qualifying ✓' if quali_used else 'season avg (Q3 unavailable)'}")
    print("\n  Feature importances (XGBClassifier):")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp / 2)
        print(f"    {feat:<25} {bar:<25} {imp:.1f}%")

    grid_imp = importances.get("grid_position", 0)
    pen_imp  = importances.get("monaco_grid_penalty", 0)
    print(f"\n  Combined grid signal: {grid_imp + pen_imp:.1f}%")

    print("\n  Full top 10:")
    print(f"  {'POS':<5} {'DRV':<6} {'TEAM':<25} {'PROB'}")
    print("  " + "─" * 48)
    for entry in full_grid[:10]:
        print(f"  P{entry['position']:<4} {entry['driver']:<6} {entry['team']:<25} {entry['podiumProb']:>5.1f}%")

    save_json(full_grid, importances, feature_cols, tuning_summary, quali_used)

    print("\n  NEXT STEPS:")
    if not QUALIFYING_DONE:
        print("  1. Saturday — set QUALIFYING_DONE=True, USE_GRID_POSITION=True")
        print("  2. Rerun: python backend/scripts/monaco_prediction.py")
    else:
        print("  1. After Sunday race → fill actualResult in monaco-2026.json")
        print("  2. Hit /clear-cache to refresh dashboard")
    print("=" * 65)


if __name__ == "__main__":
    main()
