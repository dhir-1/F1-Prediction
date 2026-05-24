"""
canada_prediction.py
────────────────────
Dhir's Pit Wall · R5 Canadian Grand Prix 2026
Circuit Gilles-Villeneuve, Montréal

Approach:
- No grid position
- VotingClassifier (soft): XGBClassifier + XGBRegressorClassifier + RandomForest
- GridSearch 3-fold for tuning
- 9 base features, plus sprint_position after sprint is available
- Two-pass: run before sprint (SPRINT_DONE=False), run again after (SPRINT_DONE=True)

Run:
    python backend/scripts/canada_prediction.py

Output:
    backend/data/predictions/canada-2026.json
"""

import json
import warnings
import numpy as np
import pandas as pd
import fastf1

from pathlib import Path
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import GridSearchCV, cross_val_score
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
CACHE_DIR   = BACKEND_DIR / "data" / "fastf1_cache"
OUTPUT_FILE = BACKEND_DIR / "data" / "predictions" / "canada-2026.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


# =============================================================================
# SECTION 0 — SETTINGS  (only section you ever need to edit)
# =============================================================================

TRAINING_RACES = [
    (2026, "Australia", "R"),
    (2026, "China",     "R"),
    (2026, "Japan",     "R"),
    (2026, "Miami",     "R"),
]

# ── Sprint flag ───────────────────────────────────────────────────────────────
# Before Saturday sprint  → SPRINT_DONE = False
# After Saturday sprint   → SPRINT_DONE = True, fill SPRINT_RESULTS below
# ─────────────────────────────────────────────────────────────────────────────
SPRINT_DONE = True

# Fill these in after Saturday's sprint race (position 1–20)
# Key = driver 3-letter code, Value = finishing position in sprint
SPRINT_RESULTS = {
    "RUS": 1,
    "NOR": 2,
    "ANT": 3,
    "PIA": 4,
    "LEC": 5,
    "HAM": 6,
    "VER": 7,
    "LIN": 8,
    "COL": 9,
    "SAI": 10,
    "LAW": 11,
    "BOR": 12,
    "OCO": 13,
    "PER": 14,
    "HUL": 15,
    "STR": 16,
    "BOT": 17,
    "BEA": 18,
    "ALB": 19,
    "GAS": 20,
    "HAD": 21,
    "ALO": 22,
}

# Max championship points available per race (for reliability score)
MAX_POINTS_PER_RACE = 25
TOTAL_RACES         = len(TRAINING_RACES)
MAX_POSSIBLE_POINTS = MAX_POINTS_PER_RACE * TOTAL_RACES  # 100


# =============================================================================
# SECTION 1 — FEATURE COLUMNS
# =============================================================================

# Base features (no sprint)
BASE_FEATURES = [
    "avg_finish_last3",
    "finish_trend",
    "points_per_race",
    "avg_lap_time_delta",
    "constructor_avg_finish",
    "tyre_consistency",
    "avg_grid_position",
    "dnf_count",
    "reliability_score",
]

# Sprint feature added after Saturday
SPRINT_FEATURE = ["sprint_position"]

def get_feature_cols() -> list[str]:
    return BASE_FEATURES + SPRINT_FEATURE if SPRINT_DONE else BASE_FEATURES


# =============================================================================
# SECTION 2 — LOAD SESSIONS
# =============================================================================

def load_sessions() -> list:
    print(f"\n[1/5] Loading {len(TRAINING_RACES)} race sessions...")
    sessions = []
    for year, race, stype in TRAINING_RACES:
        print(f"  → {year} {race}...", end=" ", flush=True)
        sess = fastf1.get_session(year, race, stype)
        sess.load(laps=True, telemetry=False, weather=False, messages=False)
        sessions.append(sess)
        print(f"✓ {len(sess.results)} drivers")
    print(f"  ✓ All sessions loaded")
    return sessions


def load_historical_sprint_positions(race_sessions: list) -> dict[tuple[str, str], float]:
    """
    Load actual sprint finishing positions for prior 2026 sprint weekends.
    Keys are (race_name, driver_code).
    """
    if not SPRINT_DONE:
        return {}

    print("\n[1b/5] Loading historical sprint sessions...")
    sprint_positions: dict[tuple[str, str], float] = {}

    for race_session in race_sessions:
        event_format = str(race_session.event.get("EventFormat", "")).lower()
        race_name = str(race_session.event["EventName"])

        if "sprint" not in event_format:
            continue

        event_date = pd.Timestamp(race_session.event["EventDate"])
        year = int(event_date.year)

        print(f"  → {year} {race_name} sprint...", end=" ", flush=True)
        try:
            sprint_session = fastf1.get_session(year, race_name, "S")
            sprint_session.load(laps=False, telemetry=False, weather=False, messages=False)

            count = 0
            for _, row in sprint_session.results.sort_values("Position").iterrows():
                code = str(row.get("Abbreviation", "")).strip().upper()
                pos = row.get("Position", np.nan)
                if code and pd.notna(pos):
                    sprint_positions[(race_name, code)] = float(pos)
                    count += 1

            print(f"✓ {count} drivers")
        except Exception as exc:
            print(f"skipped ({exc})")

    if sprint_positions:
        print(f"  ✓ Loaded {len(sprint_positions)} historical sprint-position values")
    else:
        print("  ! No historical sprint sessions loaded")

    return sprint_positions


# =============================================================================
# SECTION 3 — COMPUTE PER-RACE FEATURES
# =============================================================================

def compute_race_features(sessions: list) -> pd.DataFrame:
    print("\n[2/5] Computing race features...")
    all_rows = []

    for sess_idx, sess in enumerate(sessions):
        results   = sess.results
        laps      = sess.laps
        race_name = sess.event["EventName"]

        # Winner avg lap time for delta calculation
        winner_code = results.sort_values("Position").iloc[0]["Abbreviation"]
        winner_laps = laps.pick_drivers(winner_code).pick_quicklaps()
        winner_avg_lap = (
            winner_laps["LapTime"].dropna()
                        .apply(lambda t: t.total_seconds())
                        .mean()
            if not winner_laps.empty else None
        )

        for _, driver in results.iterrows():
            code       = str(driver["Abbreviation"]).strip().upper()
            finish_pos = float(driver.get("Position",     20) or 20)
            grid_pos   = float(driver.get("GridPosition", 10) or 10)
            points     = float(driver.get("Points",        0) or  0)
            team       = str(driver.get("TeamName", "Unknown"))
            status     = str(driver.get("Status", ""))

            # DNF flag — anything not a classified finish
            is_dnf = 1 if (
                status not in ("Finished",)
                and "Lap" not in status
                and "+" not in status
            ) else 0

            # Driver laps
            drv_laps = laps.pick_drivers(code)

            # Avg lap time delta vs race winner
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

            # Tyre consistency — std dev of lap times within stints
            consistency_vals = []
            if "Stint" in drv_laps.columns:
                for stint_num in drv_laps["Stint"].dropna().unique():
                    stint_laps = drv_laps[
                        (drv_laps["Stint"] == stint_num) &
                        (drv_laps["PitInTime"].isna()) &
                        (drv_laps["PitOutTime"].isna())
                    ]
                    clean = stint_laps["LapTime"].dropna()
                    if len(clean) > 3:
                        times_s = clean.apply(lambda t: t.total_seconds())
                        consistency_vals.append(times_s.std())
            tyre_consistency = np.mean(consistency_vals) if consistency_vals else 1.5

            all_rows.append({
                "driver":             code,
                "team":               team,
                "race":               race_name,
                "sess_idx":           sess_idx,
                # raw values for rolling
                "finish_position":    finish_pos,
                "grid_position":      grid_pos,
                "points":             points,
                "is_dnf":             is_dnf,
                # per-race features
                "avg_lap_time_delta": avg_lap_time_delta,
                "tyre_consistency":   tyre_consistency,
                # target
                "podium":             1 if finish_pos <= 3 else 0,
            })

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)
    print(f"  ✓ {len(df)} rows across {df['race'].nunique()} races")
    return df


# =============================================================================
# SECTION 4 — ROLLING & SEASON FEATURES
# =============================================================================

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[3/5] Adding rolling features...")
    df = df.copy()

    # avg_finish_last3
    df["avg_finish_last3"] = (
        df.groupby("driver")["finish_position"]
          .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # finish_trend — slope of recent finishes (negative = improving)
    def compute_trend(series):
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

    df["finish_trend"] = (
        df.groupby("driver")["finish_position"]
          .transform(compute_trend)
    )

    # points_per_race
    df["cumulative_points"] = df.groupby("driver")["points"].cumsum()
    df["race_number"]       = df.groupby("driver").cumcount() + 1
    df["points_per_race"]   = df["cumulative_points"] / df["race_number"]

    # constructor_avg_finish
    df["constructor_avg_finish"] = (
        df.groupby(["race", "team"])["finish_position"]
          .transform("mean")
    )

    # avg_grid_position (season average so far)
    df["avg_grid_position"] = (
        df.groupby("driver")["grid_position"]
          .transform(lambda x: x.expanding().mean())
    )

    # dnf_count — cumulative DNFs across season
    df["dnf_count"] = (
        df.groupby("driver")["is_dnf"]
          .transform(lambda x: x.cumsum())
    )

    # reliability_score — points scored vs max possible
    # Higher = more reliable. A DNF from P1 hurts far more than DNF from P20.
    df["reliability_score"] = df["cumulative_points"] / MAX_POSSIBLE_POINTS

    podium_dist = df["podium"].value_counts().to_dict()
    print(f"  ✓ Podium distribution: {podium_dist}")
    print(f"  ✓ DNF distribution: {df['is_dnf'].value_counts().to_dict()}")
    print(f"  ✓ Drivers with DNFs: {df[df['dnf_count'] > 0]['driver'].unique().tolist()}")

    return df


def attach_historical_sprint_feature(
    df: pd.DataFrame,
    sprint_positions: dict[tuple[str, str], float],
) -> pd.DataFrame:
    """
    For sprint weekends in the historical sample, use the real sprint result.
    For non-sprint weekends, fall back to grid position as a Saturday-order proxy.
    """
    if not SPRINT_DONE:
        return df

    df = df.copy()

    has_real_sprint = []
    sprint_values = []
    for _, row in df.iterrows():
        key = (str(row["race"]), str(row["driver"]))
        if key in sprint_positions:
            sprint_values.append(float(sprint_positions[key]))
            has_real_sprint.append(True)
        else:
            sprint_values.append(float(row["grid_position"]))
            has_real_sprint.append(False)

    df["sprint_position"] = sprint_values

    real_count = int(sum(has_real_sprint))
    fallback_count = int(len(df) - real_count)
    print(
        f"  ✓ Sprint feature attached: {real_count} rows from real sprint results, "
        f"{fallback_count} rows from grid fallback"
    )

    return df


# =============================================================================
# SECTION 5 — XGBREGRESSOR WRAPPER
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
        super().__init__()
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
# SECTION 6 — GRIDSEARCH + VOTING CLASSIFIER
# =============================================================================

def tune_and_build_voting_classifier(X_train: np.ndarray, y_train: np.ndarray):
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    spw   = n_neg / n_pos if n_pos > 0 else 1.0

    # XGBClassifier
    print("\n  Tuning XGBClassifier...")
    xgb_cls_gs = GridSearchCV(
        XGBClassifier(
            scale_pos_weight=spw,
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
            random_state=42,
        ),
        param_grid={
            "n_estimators":     [50, 100],
            "max_depth":        [2, 3],
            "learning_rate":    [0.05, 0.1],
            "subsample":        [0.7, 0.8],
            "colsample_bytree": [0.7, 0.8],
        },
        cv=3, scoring="f1", n_jobs=-1, refit=True,
    )
    xgb_cls_gs.fit(X_train, y_train)
    best_xgb_cls = xgb_cls_gs.best_estimator_
    print(f"    Best params : {xgb_cls_gs.best_params_}")
    print(f"    Best CV F1  : {xgb_cls_gs.best_score_:.3f}")

    # XGBRegressorClassifier
    print("\n  Tuning XGBRegressorClassifier...")
    best_xgb_reg   = None
    best_reg_score = -1.0
    for ne in [50, 100]:
        for md in [2, 3]:
            for lr in [0.05, 0.1]:
                candidate = XGBRegressorClassifier(
                    n_estimators=ne, max_depth=md,
                    learning_rate=lr, subsample=0.8,
                    colsample_bytree=0.8, random_state=42,
                )
                try:
                    scores     = cross_val_score(candidate, X_train, y_train, cv=3, scoring="f1")
                    mean_score = scores.mean()
                    if mean_score > best_reg_score:
                        best_reg_score = mean_score
                        best_xgb_reg   = candidate
                except Exception:
                    continue

    if best_xgb_reg is None:
        best_xgb_reg = XGBRegressorClassifier()
    best_xgb_reg.fit(X_train, y_train)
    print(f"    Best CV F1  : {best_reg_score:.3f}")

    # RandomForest
    print("\n  Tuning RandomForestClassifier...")
    rf_gs = GridSearchCV(
        RandomForestClassifier(class_weight="balanced", random_state=42),
        param_grid={
            "n_estimators":      [100, 200],
            "max_depth":         [3, 4, None],
            "min_samples_split": [2, 5],
        },
        cv=3, scoring="f1", n_jobs=-1, refit=True,
    )
    rf_gs.fit(X_train, y_train)
    best_rf = rf_gs.best_estimator_
    print(f"    Best params : {rf_gs.best_params_}")
    print(f"    Best CV F1  : {rf_gs.best_score_:.3f}")

    # Soft VotingClassifier
    print("\n  Building VotingClassifier (soft voting)...")
    voting_clf = VotingClassifier(
        estimators=[
            ("xgb_cls", best_xgb_cls),
            ("xgb_reg", best_xgb_reg),
            ("rf",      best_rf),
        ],
        voting="soft",
    )
    voting_clf.fit(X_train, y_train)
    print("  ✓ VotingClassifier trained")

    return voting_clf, best_xgb_cls


# =============================================================================
# SECTION 7 — BUILD CANADA PREDICTION ROWS
# =============================================================================

def build_canada_rows(df: pd.DataFrame, sessions: list) -> pd.DataFrame:
    """
    One row per driver using full 2026 history.
    Sprint position added if SPRINT_DONE = True.
    """
    last_results = sessions[-1].results
    rows = []

    for _, driver in last_results.iterrows():
        code = str(driver["Abbreviation"]).strip().upper()
        team = str(driver.get("TeamName", "Unknown"))

        drv_history = df[df["driver"] == code].sort_values("sess_idx")

        if drv_history.empty:
            row = {feat: 0.0 for feat in get_feature_cols()}
            row.update({
                "driver":         code,
                "team":           team,
                "grid_position":  10,
                "grid_source":    "No 2026 data",
            })
            rows.append(row)
            continue

        last = drv_history.iloc[-1]

        row = {
            "driver":                  code,
            "team":                    team,
            # display only — not in FEATURE_COLS
            "grid_position":           10,
            "grid_source":             "Not used",
            # 9 base features
            "avg_finish_last3":        float(last["avg_finish_last3"]),
            "finish_trend":            float(last["finish_trend"]),
            "points_per_race":         float(last["points_per_race"]),
            "avg_lap_time_delta":      float(drv_history["avg_lap_time_delta"].mean()),
            "constructor_avg_finish":  float(last["constructor_avg_finish"]),
            "tyre_consistency":        float(drv_history["tyre_consistency"].mean()),
            "avg_grid_position":       float(last["avg_grid_position"]),
            "dnf_count":               float(last["dnf_count"]),
            "reliability_score":       float(last["reliability_score"]),
        }

        # Sprint feature
        if SPRINT_DONE:
            row["sprint_position"] = float(SPRINT_RESULTS.get(code, 15))

        rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 8 — PREDICT & RANK
# =============================================================================

def predict_canada(voting_clf, xgb_cls, canada_df: pd.DataFrame) -> tuple[list, dict]:
    feature_cols = get_feature_cols()
    X_canada     = canada_df[feature_cols].fillna(0).values

    probs                    = voting_clf.predict_proba(X_canada)[:, 1]
    canada_df                = canada_df.copy()
    canada_df["podium_prob"] = probs
    canada_df                = canada_df.sort_values(
        "podium_prob", ascending=False
    ).reset_index(drop=True)
    canada_df["predicted_position"] = canada_df.index + 1

    # Feature importances from XGBClassifier leg
    importances = {}
    if hasattr(xgb_cls, "feature_importances_"):
        for feat, imp in zip(feature_cols, xgb_cls.feature_importances_):
            importances[feat] = round(float(imp), 4)

    full_grid = [
        {
            "position":      int(row["predicted_position"]),
            "driver":        row["driver"],
            "team":          row["team"],
            "podium_prob":   round(float(row["podium_prob"]) * 100, 1),
            "grid_position": int(row.get("grid_position", 10)),
            "grid_source":   str(row.get("grid_source", "Not used")),
        }
        for _, row in canada_df.iterrows()
    ]

    return full_grid, importances


# =============================================================================
# SECTION 9 — SAVE JSON
# =============================================================================

def save_json(full_grid: list, importances: dict, feature_cols: list) -> None:
    podium = full_grid[:3]
    status = "Post-Sprint Prediction" if SPRINT_DONE else "Pre-Sprint Prediction"

    sprint_note = (
        "Sprint result included as a feature. Historical sprint weekends like China and Miami use their real sprint classifications, while non-sprint weekends fall back to grid position as the Saturday-order proxy."
        if SPRINT_DONE else
        "Sprint result not yet included. Rerun after Saturday sprint to incorporate real pace data."
    )

    output = {
        # identity
        "slug":     "canadian-grand-prix",
        "raceName": "Canadian Grand Prix",
        "round":    5,
        "circuit":  "Circuit Gilles-Villeneuve",
        "date":     "2026-05-24",
        "status":   status,

        # model
        "modelUsed":       "VotingClassifier (XGB · XGBReg · RF)",
        "qualifying_done": False,

        # prediction
        "predictedPodium": [
            {
                "pos":        p["position"],
                "driver":     p["driver"],
                "team":       p["team"],
                "confidence": p["podium_prob"],
            }
            for p in podium
        ],
        "fullGrid": full_grid,

        # features
        "features":           feature_cols,
        "featureImportances": importances,

        # metrics empty — no LORO
        "metrics": {
            "f1":        0.0,
            "precision": 0.0,
            "recall":    0.0,
            "roc_auc":   0.0,
        },

        # training
        "trainingData": {
            "races":    ["Australia", "China", "Japan", "Miami"],
            "rows":     88,
            "cvMethod": "Full Train · GridSearch 3-Fold (tuning only)",
        },

        # post-race — fill after Sunday
        "actualResult": [],

        # pit wall notes
        "pitWallNotes": [
            "Grid position excluded by design — in Miami it had 57% importance and dominated the output unfairly.",
            sprint_note,
            "reliability_score captures DNF cost weighted by race position — a DNF from P1 hurts far more than a DNF from P20.",
            "Both Mercedes and McLaren are bringing upgrade packages to Canada. McLaren's new front wing targets aerodynamic efficiency on Montreal's long straights.",
            "Cadillac brings Canada-specific upgrades: new front brake drums, diffuser trim, winglets and front torsion bars to improve curb riding at Circuit Gilles-Villeneuve.",
            "Canada is a stop-start circuit with no high speed corners — where Mercedes' typical advantage is smallest. Rain and cold (as low as 14°C) could shuffle the order further.",
        ],

        # limitations
        "limitations": [
            "Only 88 training rows across 4 dry permanent circuits — wet and street circuit features carry zero signal.",
            "Mercedes 2026 dominance may cause model to overweight ANT and RUS regardless of Canada-specific pace.",
            "Upgrade impact (McLaren front wing, Mercedes package, Cadillac curb kit) is not capturable from historical data.",
            f"{len(feature_cols)} features used — dead features (pit times, positions gained, tyre life) dropped due to insufficient variance in training data.",
            "Sprint weekends in the historical sample use real sprint results, but non-sprint weekends still fall back to grid position for that feature.",
            "Sprint result added post-Saturday gives real pace signal but is still from a shorter race format.",
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
    sprint_status = "Post-Sprint" if SPRINT_DONE else "Pre-Sprint"
    feature_cols = get_feature_cols()
    print("=" * 65)
    print(f"  DHIR'S PIT WALL — R5 Canadian Grand Prix 2026")
    print(f"  VotingClassifier · {len(feature_cols)} Features · {sprint_status}")
    print("=" * 65)

    # 1. Load
    sessions = load_sessions()
    historical_sprint_positions = load_historical_sprint_positions(sessions)

    # 2. Compute per-race features
    race_df = compute_race_features(sessions)

    # 3. Rolling features
    race_df = add_rolling_features(race_df)
    race_df = attach_historical_sprint_feature(race_df, historical_sprint_positions)

    # 4. Train
    print("\n[4/5] Training VotingClassifier with GridSearch...")
    X_train      = race_df[feature_cols].fillna(0).values
    y_train      = race_df["podium"].values
    voting_clf, best_xgb_cls = tune_and_build_voting_classifier(X_train, y_train)

    # 5. Predict
    print("\n[5/5] Building Canada prediction rows...")
    canada_df = build_canada_rows(race_df, sessions)
    full_grid, importances = predict_canada(voting_clf, best_xgb_cls, canada_df)

    # Print
    print("\n" + "=" * 65)
    print(f"  🏁  CANADIAN GP PREDICTED PODIUM ({sprint_status})")
    print("=" * 65)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for entry in full_grid[:3]:
        print(
            f"  {medals[entry['position']]}  "
            f"P{entry['position']}  "
            f"{entry['driver']:<6}  "
            f"{entry['team']:<28}  "
            f"{entry['podium_prob']}%"
        )

    print("\n  Feature importances (XGBClassifier):")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"    {feat:<28} {bar}  {imp:.4f}")

    print("\n  Full top 10:")
    print(f"  {'POS':<5} {'DRV':<6} {'TEAM':<28} {'PROB'}")
    print("  " + "─" * 52)
    for entry in full_grid[:10]:
        print(
            f"  P{entry['position']:<4} "
            f"{entry['driver']:<6} "
            f"{entry['team']:<28} "
            f"{entry['podium_prob']:>5.1f}%"
        )

    save_json(full_grid, importances, feature_cols)

    print("\n  NEXT STEPS:")
    if not SPRINT_DONE:
        print("  1. Saturday — watch sprint race")
        print("  2. Fill SPRINT_RESULTS dict with actual positions")
        print("  3. Set SPRINT_DONE = True")
        print("  4. Rerun: python backend/scripts/canada_prediction.py")
    else:
        print("  1. After Sunday GP → fill actualResult in canada-2026.json")
        print("  2. Hit /clear-cache to refresh dashboard")
    print("=" * 65)


if __name__ == "__main__":
    main()
