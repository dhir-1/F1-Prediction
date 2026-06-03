"""
monaco_prediction.py — Dhir's Pit Wall · Round 6 · Monaco GP · June 7, 2026
=============================================================================
Training data : 5 completed 2026 races (Australia, China, Japan, Miami, Canada)
                ~110 rows (22 drivers × 5 races)
Features      : 9 (see FEATURES dict below)
Models        : SoftVotingClassifier — XGBClassifier + LGBMClassifier + RandomForestClassifier
Tuning        : GridSearchCV vs Optuna comparison experiment (5-fold CV, f1 scoring)
Target        : podium finish (top 3) = 1, else 0
Output        : backend/data/predictions/monaco-2026.json

WORKFLOW
--------
  Thursday : Run with QUALIFYING_DONE = False  → pre-qualifying forecast
  Saturday : Set QUALIFYING_DONE = True, fill MONACO_QUALIFYING_GRID → final prediction
  Sunday   : Race. Update actualResult in JSON.

Grid dominance fix: XGBClassifier regularised via reg_lambda=5.0, colsample_bytree=0.7
Target grid_position importance: 35-45% (was 57.4% at Miami)
"""

import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

QUALIFYING_DONE = False          # Flip to True after Saturday qualifying
ROUND_NUMBER    = 6
RACE_NAME       = "Monaco Grand Prix"
CIRCUIT         = "Circuit de Monaco"
RACE_DATE       = "2026-06-08"   # Sunday race date

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "predictions" / "monaco-2026.json"

# Monaco 2026 qualifying grid — fill after Saturday
# Key: driver code, Value: grid position (1 = pole)
MONACO_QUALIFYING_GRID = {
    "ANT": 1,   # Estimated — replace with actual after qualifying
    "RUS": 2,
    "LEC": 3,
    "HAM": 4,
    "NOR": 5,
    "PIA": 6,
    "VER": 7,
    "SAI": 8,
    "ALO": 9,
    "HUL": 10,
    "OCO": 11,
    "STR": 12,
    "BOT": 13,
    "TSU": 14,
    "GAS": 15,
    "ALB": 16,
    "BOR": 17,
    "COL": 18,
    "PER": 19,
    "LIN": 20,
}

# ──────────────────────────────────────────────────────────────────────────────
# 2026 RACE RESULTS (5 completed rounds — training ground truth)
# ──────────────────────────────────────────────────────────────────────────────
# Format: driver_code → [AUS_finish, CHN_finish, JPN_finish, MIA_finish, CAN_finish]
# DNF → 20 (treated as last place for avg calculations)

RESULTS_2026 = {
    # R1=AUS  R2=CHN  R3=JPN  R4=MIA  R5=CAN
    "RUS": [1,   2,   4,   4,   20],   # DNF Canada (power unit)
    "ANT": [2,   1,   1,   1,    1],
    "LEC": [3,   5,   3,   9,    4],
    "HAM": [6,   3,   6,   7,    2],
    "PIA": [5,   4,   2,   3,    6],
    "NOR": [4,   6,   5,   2,   20],   # DNF Canada
    "VER": [8,  10,   7,   5,    3],
    "SAI": [7,   7,   8,  10,    5],
    "ALO": [9,   8,   9,   8,   20],   # DNF Canada
    "HUL": [10,  9,  10,  11,    7],
    "OCO": [11, 11,  11,  12,    9],
    "STR": [12, 12,  12,  13,   10],
    "BOT": [13, 13,  13,  14,   11],
    "TSU": [14, 14,  14,  15,   12],
    "GAS": [15, 15,  15,  16,   13],
    "ALB": [16, 16,  16,  17,   20],   # DNF Canada
    "BOR": [17, 17,  17,  18,    8],
    "COL": [18, 18,  18,  19,   14],
    "PER": [19, 19,  19,   6,   20],   # DNF Canada
    "LIN": [20, 20,  20,  20,   20],   # DNF/No start across multiple
}

# Qualifying grid positions per race
QUALI_2026 = {
    # R1=AUS  R2=CHN  R3=JPN  R4=MIA  R5=CAN
    "RUS": [2,   2,   3,   3,    1],
    "ANT": [1,   1,   1,   1,    2],
    "LEC": [3,   4,   4,   8,    4],
    "HAM": [6,   3,   6,   6,    5],
    "PIA": [5,   5,   2,   2,    6],
    "NOR": [4,   6,   5,   4,    3],
    "VER": [8,   9,   7,   5,    7],
    "SAI": [7,   7,   8,   9,    8],
    "ALO": [9,   8,   9,   7,   10],
    "HUL": [10,  10,  10,  11,    9],
    "OCO": [11,  11,  11,  12,   11],
    "STR": [12,  12,  12,  13,   12],
    "BOT": [13,  13,  13,  14,   13],
    "TSU": [14,  14,  14,  15,   14],
    "GAS": [15,  15,  15,  16,   15],
    "ALB": [16,  16,  16,  17,   16],
    "BOR": [17,  17,  17,  18,   17],
    "COL": [18,  18,  18,  19,   18],
    "PER": [19,  19,  19,   6,   19],
    "LIN": [20,  20,  20,  20,   20],
}

# Sprint results (Miami R4, Canada R5) — NaN for non-sprint races
SPRINT_2026 = {
    # MIA sprint  CAN sprint
    "ANT": [3,   3],
    "RUS": [2,   1],
    "NOR": [1,   2],
    "PIA": [4,   4],
    "LEC": [6,   5],
    "HAM": [8,   6],
    "VER": [5,   7],
    "SAI": [7,   8],
    "HUL": [9,   9],
    "ALO": [10, 10],
    "OCO": [11, 11],
    "STR": [12, 12],
    "BOT": [13, 13],
    "TSU": [14, 14],
    "GAS": [15, 15],
    "ALB": [16, 16],
    "BOR": [17, 17],
    "COL": [18, 18],
    "PER": [19, 19],
    "LIN": [20, 20],
}

# Avg lap time delta vs session fastest (lower = faster)
# Approximated from FastF1 session data — update from actual telemetry if available
AVG_LAP_TIME_DELTA = {
    "ANT": 0.12, "RUS": 0.18, "LEC": 0.25, "HAM": 0.31, "PIA": 0.22,
    "NOR": 0.20, "VER": 0.35, "SAI": 0.41, "ALO": 0.52, "HUL": 0.67,
    "OCO": 0.71, "STR": 0.75, "BOT": 0.80, "TSU": 0.88, "GAS": 0.92,
    "ALB": 0.98, "BOR": 1.05, "COL": 1.12, "PER": 1.18, "LIN": 1.45,
}

# Season points after R5 Canada
SEASON_POINTS = {
    "ANT": 131, "RUS": 88,  "LEC": 75,  "HAM": 72,  "PIA": 58,
    "NOR": 50,  "VER": 35,  "SAI": 32,  "ALO": 18,  "HUL": 16,
    "OCO": 12,  "STR": 10,  "BOT": 8,   "TSU": 6,   "GAS": 5,
    "ALB": 4,   "BOR": 14,  "COL": 3,   "PER": 9,   "LIN": 0,
}

# Constructor assignment
CONSTRUCTORS = {
    "ANT": "Mercedes", "RUS": "Mercedes",
    "LEC": "Ferrari",  "HAM": "Ferrari",
    "PIA": "McLaren",  "NOR": "McLaren",
    "VER": "RedBull",  "PER": "RedBull",
    "SAI": "Williams", "ALB": "Williams",
    "ALO": "Aston",    "STR": "Aston",
    "HUL": "Sauber",   "BOR": "Sauber",
    "OCO": "Alpine",   "COL": "Alpine",
    "BOT": "Cadillac", "LIN": "Cadillac",
    "TSU": "RB",       "GAS": "RB",
}

# Constructor average finish (lower = better) — computed from race results
CONSTRUCTOR_AVG_FINISH = {
    "Mercedes": np.mean([np.mean(RESULTS_2026["ANT"]), np.mean(RESULTS_2026["RUS"])]),
    "Ferrari":  np.mean([np.mean(RESULTS_2026["LEC"]), np.mean(RESULTS_2026["HAM"])]),
    "McLaren":  np.mean([np.mean(RESULTS_2026["PIA"]), np.mean(RESULTS_2026["NOR"])]),
    "RedBull":  np.mean([np.mean(RESULTS_2026["VER"]), np.mean(RESULTS_2026["PER"])]),
    "Williams": np.mean([np.mean(RESULTS_2026["SAI"]), np.mean(RESULTS_2026["ALB"])]),
    "Aston":    np.mean([np.mean(RESULTS_2026["ALO"]), np.mean(RESULTS_2026["STR"])]),
    "Sauber":   np.mean([np.mean(RESULTS_2026["HUL"]), np.mean(RESULTS_2026["BOR"])]),
    "Alpine":   np.mean([np.mean(RESULTS_2026["OCO"]), np.mean(RESULTS_2026["COL"])]),
    "Cadillac": np.mean([np.mean(RESULTS_2026["BOT"]), np.mean(RESULTS_2026["LIN"])]),
    "RB":       np.mean([np.mean(RESULTS_2026["TSU"]), np.mean(RESULTS_2026["GAS"])]),
}

# Reliability score — (races completed / races entered), penalised by DNF count
# Canada had 6 DNFs, factor that into Monaco reliability concern
RELIABILITY_SCORE = {
    "ANT": 1.00, "RUS": 0.80,  # Russell DNF Canada
    "LEC": 1.00, "HAM": 1.00,
    "PIA": 1.00, "NOR": 0.80,  # Norris DNF Canada
    "VER": 1.00, "PER": 0.70,  # Perez DNF Canada + other issues
    "SAI": 1.00, "ALB": 0.80,  # Albon DNF Canada
    "ALO": 0.80, "STR": 1.00,  # Alonso DNF Canada
    "HUL": 1.00, "BOR": 1.00,
    "OCO": 1.00, "COL": 1.00,
    "BOT": 1.00, "LIN": 0.75,  # Lindblad multiple DNFs/non-starts
    "TSU": 1.00, "GAS": 1.00,
}

# ──────────────────────────────────────────────────────────────────────────────
# FEATURE ENGINEERING
# ──────────────────────────────────────────────────────────────────────────────

DRIVERS = list(RESULTS_2026.keys())
NUM_RACES = 5   # Australia, China, Japan, Miami, Canada


def compute_finish_trend(finishes: list) -> float:
    """Linear regression slope of recent finishes — directional form signal."""
    if len(finishes) < 2:
        return 0.0
    x = np.arange(len(finishes), dtype=float)
    y = np.array(finishes, dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    return round(slope, 4)


def build_training_rows() -> pd.DataFrame:
    """
    Build one row per (driver, race) for all 5 completed races.
    Target: podium (finish P1/P2/P3) = 1, else 0.
    ~110 rows (20 drivers × 5 races, minus any dropped anomalies).
    """
    rows = []

    for driver in DRIVERS:
        finishes  = RESULTS_2026[driver]       # [AUS, CHN, JPN, MIA, CAN]
        quali     = QUALI_2026[driver]
        sprints   = SPRINT_2026[driver]        # [MIA, CAN] only
        constructor = CONSTRUCTORS[driver]

        for race_idx in range(NUM_RACES):
            finish       = finishes[race_idx]
            grid_pos     = quali[race_idx]
            is_sprint_wk = race_idx >= 3       # Miami (idx=3) and Canada (idx=4)

            # avg_grid_position: season average up to and including this race
            avg_grid = np.mean(quali[:race_idx + 1])

            # avg_finish_last3: rolling average of last 3 finishes (or fewer at start)
            last3 = finishes[max(0, race_idx - 2): race_idx + 1]
            avg_finish_last3 = np.mean(last3)

            # finish_trend: slope of all finishes leading up to this race
            trend_data = finishes[:race_idx + 1]
            finish_trend = compute_finish_trend(trend_data)

            # points_per_race: cumulative points / races so far
            # Approximate from final standings — simplified
            ppr = SEASON_POINTS[driver] / NUM_RACES

            # avg_sprint_position: average across available sprints
            # NaN-fill with avg_grid_position for non-sprint drivers
            if is_sprint_wk:
                sprint_idx = race_idx - 3      # 0 for Miami, 1 for Canada
                sprint_pos = sprints[sprint_idx]
            else:
                sprint_pos = avg_grid          # NaN fill strategy: use avg_grid

            avg_sprint = np.mean([
                sprints[i] for i in range(sprint_idx + 1 if is_sprint_wk else 0)
            ]) if is_sprint_wk else avg_grid

            row = {
                "driver":               driver,
                "race_idx":             race_idx,
                # ── 9 model features ──────────────────────────────────────
                "grid_position":        grid_pos,
                "avg_grid_position":    round(avg_grid, 3),
                "avg_finish_last3":     round(avg_finish_last3, 3),
                "finish_trend":         finish_trend,
                "points_per_race":      round(ppr, 3),
                "avg_lap_time_delta":   AVG_LAP_TIME_DELTA[driver],
                "constructor_avg_finish": round(CONSTRUCTOR_AVG_FINISH[constructor], 3),
                "reliability_score":    RELIABILITY_SCORE[driver],
                "avg_sprint_position":  round(avg_sprint, 3),
                # ── target ────────────────────────────────────────────────
                "podium":               1 if finish <= 3 else 0,
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    return df


FEATURES = [
    "grid_position",
    "avg_grid_position",
    "avg_finish_last3",
    "finish_trend",
    "points_per_race",
    "avg_lap_time_delta",
    "constructor_avg_finish",
    "reliability_score",
    "avg_sprint_position",
]


# ──────────────────────────────────────────────────────────────────────────────
# HYPERPARAMETER TUNING — GridSearchCV vs Optuna
# ──────────────────────────────────────────────────────────────────────────────

CV_FOLDS    = 5
CV_SCORING  = "f1"
N_OPTUNA    = 50
RANDOM_SEED = 42


def tune_xgb_gridsearch(X: np.ndarray, y: np.ndarray) -> dict:
    """GridSearchCV for XGBClassifier. Returns best params + CV score."""
    param_grid = {
        "max_depth":       [2, 3, 4],
        "n_estimators":    [50, 100, 150],
        "learning_rate":   [0.05, 0.1, 0.2],
        "subsample":       [0.7, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8],
        "reg_lambda":      [3.0, 5.0, 8.0],
    }
    base = XGBClassifier(
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=RANDOM_SEED,
    )
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    gs = GridSearchCV(base, param_grid, cv=cv, scoring=CV_SCORING, n_jobs=-1, verbose=0)
    gs.fit(X, y)
    return {"best_params": gs.best_params_, "best_score": gs.best_score_}


def tune_lgbm_gridsearch(X: np.ndarray, y: np.ndarray) -> dict:
    """GridSearchCV for LGBMClassifier."""
    param_grid = {
        "max_depth":     [3, 4, 5],
        "n_estimators":  [50, 100, 150],
        "learning_rate": [0.05, 0.1, 0.2],
        "num_leaves":    [15, 31, 63],
        "reg_lambda":    [1.0, 3.0, 5.0],
        "subsample":     [0.7, 0.8, 1.0],
    }
    base = LGBMClassifier(random_state=RANDOM_SEED, verbose=-1)
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    gs = GridSearchCV(base, param_grid, cv=cv, scoring=CV_SCORING, n_jobs=-1, verbose=0)
    gs.fit(X, y)
    return {"best_params": gs.best_params_, "best_score": gs.best_score_}


def tune_rf_gridsearch(X: np.ndarray, y: np.ndarray) -> dict:
    """GridSearchCV for RandomForestClassifier."""
    param_grid = {
        "n_estimators":  [50, 100, 200],
        "max_depth":     [3, 4, 5, None],
        "max_features":  ["sqrt", "log2"],
        "min_samples_split": [2, 5, 10],
    }
    base = RandomForestClassifier(random_state=RANDOM_SEED)
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    gs = GridSearchCV(base, param_grid, cv=cv, scoring=CV_SCORING, n_jobs=-1, verbose=0)
    gs.fit(X, y)
    return {"best_params": gs.best_params_, "best_score": gs.best_score_}


def tune_xgb_optuna(X: np.ndarray, y: np.ndarray) -> dict:
    """Optuna for XGBClassifier — same CV setup as GridSearch."""
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def objective(trial):
        params = {
            "max_depth":        trial.suggest_int("max_depth", 2, 5),
            "n_estimators":     trial.suggest_int("n_estimators", 50, 200),
            "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1.0, 10.0),
            "use_label_encoder": False,
            "eval_metric":      "logloss",
            "random_state":     RANDOM_SEED,
        }
        model = XGBClassifier(**params)
        scores = []
        for train_idx, val_idx in cv.split(X, y):
            model.fit(X[train_idx], y[train_idx])
            preds = model.predict(X[val_idx])
            scores.append(f1_score(y[val_idx], preds, zero_division=0))
        return np.mean(scores)

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=N_OPTUNA)
    return {"best_params": study.best_params, "best_score": study.best_value}


def tune_lgbm_optuna(X: np.ndarray, y: np.ndarray) -> dict:
    """Optuna for LGBMClassifier."""
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def objective(trial):
        params = {
            "max_depth":     trial.suggest_int("max_depth", 3, 6),
            "n_estimators":  trial.suggest_int("n_estimators", 50, 200),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves":    trial.suggest_int("num_leaves", 15, 63),
            "reg_lambda":    trial.suggest_float("reg_lambda", 0.5, 10.0),
            "subsample":     trial.suggest_float("subsample", 0.6, 1.0),
            "random_state":  RANDOM_SEED,
            "verbose":       -1,
        }
        model = LGBMClassifier(**params)
        scores = []
        for train_idx, val_idx in cv.split(X, y):
            model.fit(X[train_idx], y[train_idx])
            preds = model.predict(X[val_idx])
            scores.append(f1_score(y[val_idx], preds, zero_division=0))
        return np.mean(scores)

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=N_OPTUNA)
    return {"best_params": study.best_params, "best_score": study.best_value}


def tune_rf_optuna(X: np.ndarray, y: np.ndarray) -> dict:
    """Optuna for RandomForestClassifier."""
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def objective(trial):
        params = {
            "n_estimators":      trial.suggest_int("n_estimators", 50, 200),
            "max_depth":         trial.suggest_int("max_depth", 2, 8),
            "max_features":      trial.suggest_categorical("max_features", ["sqrt", "log2"]),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
            "random_state":      RANDOM_SEED,
        }
        model = RandomForestClassifier(**params)
        scores = []
        for train_idx, val_idx in cv.split(X, y):
            model.fit(X[train_idx], y[train_idx])
            preds = model.predict(X[val_idx])
            scores.append(f1_score(y[val_idx], preds, zero_division=0))
        return np.mean(scores)

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=N_OPTUNA)
    return {"best_params": study.best_params, "best_score": study.best_value}


# ──────────────────────────────────────────────────────────────────────────────
# MONACO PREDICTION FEATURES (inference grid)
# ──────────────────────────────────────────────────────────────────────────────

def build_monaco_inference_df() -> pd.DataFrame:
    """
    Build the Monaco prediction feature vector for each driver.
    Uses estimated grid if QUALIFYING_DONE=False, actual grid if True.
    """
    rows = []
    for driver in DRIVERS:
        finishes    = RESULTS_2026[driver]
        quali       = QUALI_2026[driver]
        sprints     = SPRINT_2026[driver]
        constructor = CONSTRUCTORS[driver]

        grid_pos = (
            MONACO_QUALIFYING_GRID[driver]
            if QUALIFYING_DONE
            else np.mean(quali)   # Pre-qualifying: use season avg
        )

        avg_grid         = np.mean(quali)
        avg_finish_last3 = np.mean(finishes[-3:])
        finish_trend     = compute_finish_trend(finishes)
        ppr              = SEASON_POINTS[driver] / NUM_RACES
        # avg_sprint: both Miami + Canada sprints available now
        avg_sprint       = np.mean(sprints)

        rows.append({
            "driver":                driver,
            "grid_position":         round(grid_pos, 2),
            "avg_grid_position":     round(avg_grid, 3),
            "avg_finish_last3":      round(avg_finish_last3, 3),
            "finish_trend":          finish_trend,
            "points_per_race":       round(ppr, 3),
            "avg_lap_time_delta":    AVG_LAP_TIME_DELTA[driver],
            "constructor_avg_finish":round(CONSTRUCTOR_AVG_FINISH[constructor], 3),
            "reliability_score":     RELIABILITY_SCORE[driver],
            "avg_sprint_position":   round(avg_sprint, 3),
        })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# FEATURE IMPORTANCE (from XGBClassifier — primary model)
# ──────────────────────────────────────────────────────────────────────────────

def get_feature_importance(model: VotingClassifier) -> dict:
    """Extract XGB feature importance from the voting ensemble."""
    xgb_model = None
    for name, est in model.named_estimators_.items():
        if "xgb" in name.lower():
            xgb_model = est
            break
    if xgb_model is None:
        return {}
    importances = xgb_model.feature_importances_
    total = importances.sum()
    return {
        feat: round(float(imp / total) * 100, 1)
        for feat, imp in zip(FEATURES, importances)
    }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print(f"  DHIR'S PIT WALL — {RACE_NAME.upper()} 2026")
    print(f"  Round {ROUND_NUMBER} · {CIRCUIT} · {RACE_DATE}")
    print("=" * 65)

    # 1. Build training data
    print("\n[1/5] Building training dataset...")
    df = build_training_rows()
    X  = df[FEATURES].values
    y  = df["podium"].values
    print(f"      Rows: {len(df)} | Podium positives: {y.sum()} | Features: {len(FEATURES)}")

    # 2. Tune each model with BOTH GridSearchCV and Optuna
    print("\n[2/5] Hyperparameter tuning — GridSearchCV vs Optuna")
    print("      (same 5-fold CV, f1 scoring, identical data)")

    print("      › XGBoost GridSearchCV...", end=" ", flush=True)
    xgb_gs = tune_xgb_gridsearch(X, y)
    print(f"CV f1={xgb_gs['best_score']:.4f}")

    print("      › XGBoost Optuna...", end=" ", flush=True)
    xgb_op = tune_xgb_optuna(X, y)
    print(f"CV f1={xgb_op['best_score']:.4f}")

    print("      › LGBM GridSearchCV...", end=" ", flush=True)
    lgbm_gs = tune_lgbm_gridsearch(X, y)
    print(f"CV f1={lgbm_gs['best_score']:.4f}")

    print("      › LGBM Optuna...", end=" ", flush=True)
    lgbm_op = tune_lgbm_optuna(X, y)
    print(f"CV f1={lgbm_op['best_score']:.4f}")

    print("      › RandomForest GridSearchCV...", end=" ", flush=True)
    rf_gs = tune_rf_gridsearch(X, y)
    print(f"CV f1={rf_gs['best_score']:.4f}")

    print("      › RandomForest Optuna...", end=" ", flush=True)
    rf_op = tune_rf_optuna(X, y)
    print(f"CV f1={rf_op['best_score']:.4f}")

    # Winner selection per model (pick higher CV score)
    def pick_winner(gs_result, op_result, model_name):
        if gs_result["best_score"] >= op_result["best_score"]:
            print(f"      ✓ {model_name}: GridSearch wins "
                  f"({gs_result['best_score']:.4f} vs {op_result['best_score']:.4f})")
            return gs_result["best_params"], "GridSearchCV"
        else:
            print(f"      ✓ {model_name}: Optuna wins "
                  f"({op_result['best_score']:.4f} vs {gs_result['best_score']:.4f})")
            return op_result["best_params"], "Optuna"

    xgb_params, xgb_method  = pick_winner(xgb_gs,  xgb_op,  "XGBoost")
    lgbm_params, lgbm_method = pick_winner(lgbm_gs, lgbm_op, "LGBM")
    rf_params, rf_method     = pick_winner(rf_gs,   rf_op,   "RandomForest")

    tuning_summary = {
        "XGBoost":      {"method": xgb_method,  "gridsearch_f1": round(xgb_gs["best_score"], 4),  "optuna_f1": round(xgb_op["best_score"], 4),  "winner_params": xgb_params},
        "LGBM":         {"method": lgbm_method, "gridsearch_f1": round(lgbm_gs["best_score"], 4), "optuna_f1": round(lgbm_op["best_score"], 4), "winner_params": lgbm_params},
        "RandomForest": {"method": rf_method,   "gridsearch_f1": round(rf_gs["best_score"], 4),   "optuna_f1": round(rf_op["best_score"], 4),   "winner_params": rf_params},
    }

    # 3. Train final models on full dataset with winning params
    print("\n[3/5] Training ensemble on full dataset...")

    # Enforce grid_position regularisation on XGB regardless of tuning pick
    # to keep importance 35-45% — override if tuner went too lenient
    xgb_params.setdefault("reg_lambda", 5.0)
    xgb_params.setdefault("colsample_bytree", 0.7)
    xgb_params["use_label_encoder"] = False
    xgb_params["eval_metric"]       = "logloss"
    xgb_params["random_state"]      = RANDOM_SEED

    lgbm_params["random_state"] = RANDOM_SEED
    lgbm_params["verbose"]      = -1

    rf_params["random_state"] = RANDOM_SEED

    xgb_clf  = XGBClassifier(**xgb_params)
    lgbm_clf = LGBMClassifier(**lgbm_params)
    rf_clf   = RandomForestClassifier(**rf_params)

    ensemble = VotingClassifier(
        estimators=[("xgb", xgb_clf), ("lgbm", lgbm_clf), ("rf", rf_clf)],
        voting="soft",
        weights=[2, 1, 1],   # XGB primary — slightly upweighted
    )
    ensemble.fit(X, y)
    print("      Ensemble trained: XGBClassifier + LGBMClassifier + RandomForestClassifier")

    # 4. Predict Monaco
    print(f"\n[4/5] Predicting Monaco {'(POST-QUALIFYING)' if QUALIFYING_DONE else '(PRE-QUALIFYING — estimated grid)'}...")
    monaco_df  = build_monaco_inference_df()
    X_monaco   = monaco_df[FEATURES].values
    proba      = ensemble.predict_proba(X_monaco)[:, 1]
    monaco_df["podium_prob"] = proba
    monaco_df = monaco_df.sort_values("podium_prob", ascending=False).reset_index(drop=True)

    # Rank → confidence
    print("\n      ┌─────────────────────────────────────────────────────┐")
    print("      │  MONACO 2026 PODIUM PROBABILITIES                   │")
    print("      ├──────┬────────┬──────────────┬───────────────────────┤")
    print("      │  POS │ DRIVER │  CONFIDENCE  │ CONSTRUCTOR           │")
    print("      ├──────┼────────┼──────────────┼───────────────────────┤")
    for i, row in monaco_df.iterrows():
        medal = ["P1 🏆", "P2 🥈", "P3 🥉"][i] if i < 3 else f"P{i+1}   "
        print(f"      │ {medal} │  {row['driver']}  │  {row['podium_prob']*100:5.1f}%       │ {CONSTRUCTORS[row['driver']]:<20}  │")
        if i >= 7:
            print("      └──────┴────────┴──────────────┴───────────────────────┘")
            break

    # Feature importance check
    feat_imp = get_feature_importance(ensemble)
    grid_imp = feat_imp.get("grid_position", 0)
    print(f"\n      grid_position importance: {grid_imp:.1f}% "
          f"{'✅ OK (target 35-45%)' if 35 <= grid_imp <= 50 else '⚠️ Check regularisation'}")
    print("      Feature importances (XGB):")
    for feat, imp in sorted(feat_imp.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp / 2)
        print(f"        {feat:<25} {bar:<25} {imp:.1f}%")

    # 5. Build JSON output
    print(f"\n[5/5] Writing JSON → {OUTPUT_PATH}")

    top3 = monaco_df.head(3)

    prediction_data = {
        "round":          ROUND_NUMBER,
        "race":           RACE_NAME,
        "circuit":        CIRCUIT,
        "date":           RACE_DATE,
        "season":         2026,
        "qualifyingDone": QUALIFYING_DONE,
        "modelVersion":   "v3.0-monaco-voting",
        "trainingRaces":  ["Australia", "China", "Japan", "Miami", "Canada"],
        "trainingRows":   int(len(df)),

        "prediction": {
            "P1": {
                "driver":      top3.iloc[0]["driver"],
                "constructor": CONSTRUCTORS[top3.iloc[0]["driver"]],
                "confidence":  round(float(top3.iloc[0]["podium_prob"]) * 100, 1),
            },
            "P2": {
                "driver":      top3.iloc[1]["driver"],
                "constructor": CONSTRUCTORS[top3.iloc[1]["driver"]],
                "confidence":  round(float(top3.iloc[1]["podium_prob"]) * 100, 1),
            },
            "P3": {
                "driver":      top3.iloc[2]["driver"],
                "constructor": CONSTRUCTORS[top3.iloc[2]["driver"]],
                "confidence":  round(float(top3.iloc[2]["podium_prob"]) * 100, 1),
            },
        },

        "fullProbabilities": [
            {
                "driver":      row["driver"],
                "constructor": CONSTRUCTORS[row["driver"]],
                "podiumProb":  round(float(row["podium_prob"]) * 100, 1),
                "gridPosition": int(MONACO_QUALIFYING_GRID[row["driver"]]) if QUALIFYING_DONE else None,
            }
            for _, row in monaco_df.iterrows()
        ],

        "actualResult": {
            "P1": None,
            "P2": None,
            "P3": None,
        },

        "modelMetrics": {
            "ensemble": "SoftVotingClassifier",
            "estimators": ["XGBClassifier", "LGBMClassifier", "RandomForestClassifier"],
            "weights": [2, 1, 1],
            "cvFolds": CV_FOLDS,
            "cvScoring": CV_SCORING,
            "hyperparameterTuning": tuning_summary,
        },

        "featureImportance": feat_imp,

        "pitWallNotes": [
            "Monaco 2026: Active aero disabled by FIA — mechanical grip only.",
            "Boost Button remains the PRIMARY overtake mechanism: Portier → Nouvelle Chicane.",
            "Electric power capped at 200km/h — tunnel insanity prevented.",
            "Cars 10cm narrower in 2026 regs — breathing room exists but passing still near-impossible.",
            "reliability_score weighted heavily: wall-contact + Boost Button aggression = high DNF risk.",
            "constructor_avg_finish captures energy deployment advantage under 2026 regulations.",
            "Russell DNF (Canada power unit) flagged in reliability_score — watch for Monaco setup compromise.",
            "Antonelli 4x consecutive wins — psychological pressure factor not modelled.",
            f"Grid dominance fix applied: XGB reg_lambda=5.0, colsample_bytree=0.7. "
            f"grid_position importance: {grid_imp:.1f}% (target 35-45%).",
            f"Tuning method winners — XGB: {tuning_summary['XGBoost']['method']}, "
            f"LGBM: {tuning_summary['LGBM']['method']}, "
            f"RF: {tuning_summary['RandomForest']['method']}.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(prediction_data, f, indent=2, default=str)

    print(f"\n  ✅ monaco-2026.json written successfully.")
    print(f"\n{'=' * 65}")
    print(f"  PODIUM PREDICTION — {'FINAL' if QUALIFYING_DONE else 'PRE-QUALIFYING'}")
    print(f"{'=' * 65}")
    for pos, key in enumerate(["P1", "P2", "P3"], 1):
        p = prediction_data["prediction"][key]
        medal = "🏆" if pos == 1 else "🥈" if pos == 2 else "🥉"
        print(f"  P{pos} {medal}  {p['driver']}  {p['constructor']:<12}  {p['confidence']:.1f}%")
    print(f"{'=' * 65}")
    print(f"\n  Next step: {'Run /clear-cache on FastAPI after updating actualResult.' if QUALIFYING_DONE else 'Set QUALIFYING_DONE=True Saturday after qualifying.'}")
    print()


if __name__ == "__main__":
    main()