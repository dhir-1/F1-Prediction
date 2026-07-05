"""
british_prediction.py — Dhir's Pit Wall · Round 9 · British Grand Prix · July 5, 2026
"""

import json
import warnings
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd
import optuna
from optuna.samplers import TPESampler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import f1_score
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")


# =============================================================================
# SECTION 0 — SETTINGS  (only things you ever need to change)
# =============================================================================

QUALIFYING_DONE   = True
USE_GRID_POSITION = True
IS_SPRINT         = True

ROUND_NUMBER = 9
RACE_NAME    = "British Grand Prix"
CIRCUIT      = "Silverstone Circuit"
RACE_DATE    = "2026-07-05"

# ── CHANGE THIS TO YOUR ACTUAL PATH ──────────────────────────────────────────
CACHE_DIR   = Path(r"C:\Users\dhira\Desktop\Projects\F1 Dashboard\backend\data\fastf1_cache")
OUTPUT_FILE = Path(r"C:\Users\dhira\Desktop\Projects\F1 Dashboard\backend\data\predictions\british-2026.json")
# ─────────────────────────────────────────────────────────────────────────────

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

TRAINING_RACES = [
    (2026, "Australia", "R"),
    (2026, "China",     "R"),
    (2026, "Japan",     "R"),
    (2026, "Miami",     "R"),
    (2026, "Canada",    "R"),
    (2026, "Monaco",    "R"),
    (2026, "Barcelona", "R"),
    (2026, "Austria",   "R"),
]

BRITISH_SPRINT_RESULTS = {
    "ANT": 1, "HAM": 2, "NOR": 3, "RUS": 4, "LEC": 5,
    "VER": 6, "PIA": 7, "LAW": 8, "HAD": 12, "LIN": 9,
    "HUL": 13, "BOR": 10, "SAI": 15, "BEA": 14, "GAS": 11,
    "COL": 16, "ALB": 17, "OCO": 18, "PER": 22, "BOT": 20,
    "STR": 21, "ALO": 19,
}

BRITISH_QUALIFYING_GRID = {
    "ANT": 1, "LEC": 2, "HAM": 3, "RUS": 4, "HAD": 5,
    "NOR": 6, "VER": 7, "PIA": 8, "LIN": 9, "LAW": 10,
    "BOR": 11, "HUL": 12, "BEA": 13, "SAI": 14, "GAS": 15,
    "ALB": 16, "OCO": 17, "BOT": 18, "COL": 19, "PER": 20,
    "STR": 21, "ALO": 22,
}

GRID_FLOOR_CUTOFF = 9
GRID_FLOOR_DECAY = 0.2

TOTAL_RACES = len(TRAINING_RACES)
CV_FOLDS = 5
CV_SCORING = "f1"
N_OPTUNA = 30
RANDOM_SEED = 42


# =============================================================================
# SECTION 1 — FEATURES
# =============================================================================

_ALL_FEATURES = [
    "grid_position",
    "avg_finish_last3",
    "finish_trend",
    "sprint_position",
    "avg_lap_time_delta",
    "tyre_consistency",
    "constructor_avg_finish",
    "dnf_rate",
]


def get_feature_cols():
    excluded = []
    if not USE_GRID_POSITION:
        excluded.append("grid_position")
    if not IS_SPRINT:
        excluded.append("sprint_position")
    return [f for f in _ALL_FEATURES if f not in excluded]


# =============================================================================
# SECTION 2 — LOAD QUALIFYING DELTAS + FP2 RACE-PACE PROXY
# =============================================================================

def load_quali_delta():
    if not QUALIFYING_DONE:
        return {}
    quali_deltas = {}
    try:
        q_sess = fastf1.get_session(2026, ROUND_NUMBER, "Q")
        q_sess.load(laps=True, telemetry=False, weather=False, messages=False)
        results = q_sess.results
        q3_times = []
        for _, row in results.iterrows():
            t = row.get("Q3")
            if t is not None and pd.notna(t):
                q3_times.append(t.total_seconds() if hasattr(t, "total_seconds") else float(t))
        pole_time = min(q3_times) if q3_times else None
        if pole_time is None:
            return {}
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
    except Exception:
        pass
    return quali_deltas


def load_race_pace_proxy():
    if not QUALIFYING_DONE:
        return {}
    deltas = {}
    try:
        fp2 = fastf1.get_session(2026, ROUND_NUMBER, "FP2")
        fp2.load(laps=True, telemetry=False, weather=False, messages=False)
        laps = fp2.laps
        driver_paces = {}
        for code in laps["Driver"].unique():
            drv_laps = laps.pick_drivers(code).pick_quicklaps()
            if len(drv_laps) < 5:
                continue
            times = drv_laps["LapTime"].dropna().apply(
                lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t)
            )
            if len(times) < 5:
                continue
            sorted_times = times.sort_values()
            slower_half = sorted_times.iloc[len(sorted_times) // 2:]
            driver_paces[str(code).strip().upper()] = float(slower_half.mean())
        if not driver_paces:
            return {}
        best_pace = min(driver_paces.values())
        for code, pace in driver_paces.items():
            deltas[code] = round(pace - best_pace, 3)
    except Exception:
        pass
    return deltas


def load_sprint_positions(year, race):
    try:
        s = fastf1.get_session(year, race, "S")
        s.load(laps=False, telemetry=False, weather=False, messages=False)
        results = s.results
        out = {}
        for _, row in results.iterrows():
            code = str(row.get("Abbreviation", "")).strip().upper()
            pos = row.get("Position")
            if code and pos is not None and pd.notna(pos):
                out[code] = float(pos)
        return out
    except Exception:
        return {}


# =============================================================================
# SECTION 3 — COMPUTE PER-RACE FEATURES  (loads its own sessions fresh)
# =============================================================================

def compute_race_features():
    all_rows = []
    for p in sorted(CACHE_DIR.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()

    for sess_idx, (year, race, stype) in enumerate(TRAINING_RACES):
        sess = fastf1.get_session(year, race, stype)
        sess.load(laps=True, telemetry=False, weather=False, messages=False)
        results = sess.results
        try:
            laps = sess.laps
        except Exception:
            continue
        race_name = sess.event["EventName"]

        sprint_positions = load_sprint_positions(year, race)

        winner_code = results.sort_values("Position").iloc[0]["Abbreviation"]
        winner_laps = laps.pick_drivers(winner_code).pick_quicklaps()
        winner_avg_lap = (
            winner_laps["LapTime"].dropna()
            .apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t))
            .mean()
            if not winner_laps.empty else None
        )

        for _, driver in results.iterrows():
            code = str(driver["Abbreviation"]).strip().upper()
            finish_pos = float(driver.get("Position", 20) or 20)
            grid_pos = float(driver.get("GridPosition", 11) or 11)
            points = float(driver.get("Points", 0) or 0)
            team = str(driver.get("TeamName", "Unknown"))
            status = str(driver.get("Status", ""))

            is_dnf = 1 if (
                status not in ("Finished",)
                and "Lap" not in status
                and "+" not in status
            ) else 0

            drv_laps = laps.pick_drivers(code)
            clean_laps = drv_laps.pick_quicklaps()

            if not clean_laps.empty and winner_avg_lap:
                lap_times = clean_laps["LapTime"].dropna().apply(
                    lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                )
                avg_lap_time_delta = float(lap_times.mean()) - winner_avg_lap
                tyre_consistency = float(lap_times.std()) if len(lap_times) >= 3 else 2.0
            else:
                avg_lap_time_delta = 2.0
                tyre_consistency = 2.0

            all_rows.append({
                "driver": code,
                "team": team,
                "race": race_name,
                "sess_idx": sess_idx,
                "finish_position": finish_pos,
                "grid_position": grid_pos,
                "points": points,
                "is_dnf": is_dnf,
                "avg_lap_time_delta": avg_lap_time_delta,
                "tyre_consistency": tyre_consistency,
                "podium": 1 if finish_pos <= 3 else 0,
                "sprint_position": sprint_positions.get(code, np.nan),
            })

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)
    return df


# =============================================================================
# SECTION 4 — ROLLING FEATURES
# =============================================================================

def compute_trend(series):
    vals, trends = series.values, [0.0]
    for i in range(1, len(vals)):
        window = vals[max(0, i - 3):i + 1]
        if len(window) >= 2:
            trends.append(float(np.polyfit(np.arange(len(window)), window, 1)[0]))
        else:
            trends.append(0.0)
    return pd.Series(trends, index=series.index)


def add_rolling_features(df):
    df = df.copy().sort_values(["driver", "sess_idx"]).reset_index(drop=True)

    df["avg_finish_last3"] = df.groupby("driver")["finish_position"].transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )
    df["finish_trend"] = df.groupby("driver")["finish_position"].transform(compute_trend)

    df["race_number"] = df.groupby("driver").cumcount() + 1
    df["rolling_podium_rate"] = df.groupby("driver")["podium"].transform(
        lambda x: x.ewm(span=3, adjust=False).mean()
    )

    df["avg_lap_time_delta"] = df.groupby("driver")["avg_lap_time_delta"].transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )
    df["tyre_consistency"] = df.groupby("driver")["tyre_consistency"].transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )

    df = df.sort_values(["team", "sess_idx"]).reset_index(drop=True)
    df["constructor_avg_finish"] = df.groupby("team")["finish_position"].transform(
        lambda x: x.expanding().mean()
    )
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)

    df["dnf_count"] = df.groupby("driver")["is_dnf"].transform(lambda x: x.cumsum())
    df["dnf_rate"] = df["dnf_count"] / df["race_number"]

    return df


# =============================================================================
# SECTION 5 — OPTUNA TUNING
# =============================================================================

def tune_xgb(X, y):
    spw = (y == 0).sum() / max((y == 1).sum(), 1)
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def obj(trial):
        m = XGBClassifier(
            n_estimators=trial.suggest_int("n_estimators", 50, 300),
            max_depth=trial.suggest_int("max_depth", 2, 4),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            reg_lambda=trial.suggest_float("reg_lambda", 1.0, 15.0),
            reg_alpha=trial.suggest_float("reg_alpha", 0.0, 5.0),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 5),
            scale_pos_weight=spw, use_label_encoder=False,
            eval_metric="logloss", verbosity=0, random_state=RANDOM_SEED,
        )
        return float(np.mean(cross_val_score(m, X, y, cv=cv, scoring=CV_SCORING)))

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    study.optimize(obj, n_trials=N_OPTUNA)
    best = XGBClassifier(**study.best_params, scale_pos_weight=spw,
                          use_label_encoder=False, eval_metric="logloss",
                          verbosity=0, random_state=RANDOM_SEED)
    best.fit(X, y)
    train_f1 = f1_score(y, best.predict(X))
    print(f"  XGB train f1 = {train_f1:.4f} | CV f1 = {study.best_value:.4f}")
    return best, round(study.best_value, 4)


def tune_lgbm(X, y):
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def obj(trial):
        m = LGBMClassifier(
            n_estimators=trial.suggest_int("n_estimators", 50, 300),
            max_depth=trial.suggest_int("max_depth", 2, 4),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            num_leaves=trial.suggest_int("num_leaves", 7, 31),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            reg_lambda=trial.suggest_float("reg_lambda", 0.5, 10.0),
            reg_alpha=trial.suggest_float("reg_alpha", 0.0, 5.0),
            min_child_samples=trial.suggest_int("min_child_samples", 5, 30),
            class_weight="balanced", random_state=RANDOM_SEED, verbose=-1,
        )
        return float(np.mean(cross_val_score(m, X, y, cv=cv, scoring=CV_SCORING)))

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED + 1))
    study.optimize(obj, n_trials=N_OPTUNA)
    best = LGBMClassifier(**study.best_params, class_weight="balanced",
                           random_state=RANDOM_SEED, verbose=-1)
    best.fit(X, y)
    train_f1 = f1_score(y, best.predict(X))
    print(f"  LGBM train f1 = {train_f1:.4f} | CV f1 = {study.best_value:.4f}")
    return best, round(study.best_value, 4)


# =============================================================================
# SECTION 6 — BUILD INFERENCE ROWS
# =============================================================================

def build_british_rows(df, quali_deltas, race_pace_deltas):
    feature_cols = get_feature_cols()
    austria = fastf1.get_session(2026, "Austria", "R")
    austria.load(laps=False, telemetry=False, weather=False, messages=False)
    all_drivers = austria.results

    rows = []
    for _, driver in all_drivers.iterrows():
        code = str(driver["Abbreviation"]).strip().upper()
        team = str(driver.get("TeamName", "Unknown"))

        drv_history = df[df["driver"] == code].sort_values("sess_idx")
        if drv_history.empty:
            row = {feat: np.nan for feat in feature_cols}
            row.update({"driver": code, "team": team})
            rows.append(row)
            continue

        last = drv_history.iloc[-1]
        grid_pos = float(BRITISH_QUALIFYING_GRID.get(code, 15.0)) if (USE_GRID_POSITION and QUALIFYING_DONE) else 11.0
        lap_delta = race_pace_deltas.get(
            code, quali_deltas.get(code, float(last["avg_lap_time_delta"]))
        )

        row = {
            "driver": code,
            "team": team,
            "grid_position": grid_pos,
            "avg_finish_last3": float(last["avg_finish_last3"]),
            "finish_trend": float(last["finish_trend"]),
            "sprint_position": BRITISH_SPRINT_RESULTS.get(code, np.nan),
            "avg_lap_time_delta": lap_delta,
            "tyre_consistency": float(last["tyre_consistency"]),
            "constructor_avg_finish": float(last["constructor_avg_finish"]),
            "dnf_rate": float(last["dnf_rate"]),
        }
        rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 7 — PREDICT + GRID FLOOR
# =============================================================================

def predict_british(voting_clf, best_xgb, british_df, X_train, y_train):
    feature_cols = get_feature_cols()
    X_inf = british_df[feature_cols].values

    cal_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    calibrated = CalibratedClassifierCV(estimator=voting_clf, method="sigmoid", cv=cal_cv)
    calibrated.fit(X_train, y_train)
    probs = calibrated.predict_proba(X_inf)[:, 1]

    for i, row in british_df.iterrows():
        gp = row.get("grid_position", 11)
        if gp >= GRID_FLOOR_CUTOFF:
            penalty = np.exp(-GRID_FLOOR_DECAY * (gp - GRID_FLOOR_CUTOFF + 1))
            probs[i] *= penalty

    british_df = british_df.copy()
    british_df["podium_prob"] = probs
    british_df = british_df.sort_values("podium_prob", ascending=False).reset_index(drop=True)
    british_df["predicted_pos"] = british_df.index + 1

    importances = {}
    if hasattr(best_xgb, "feature_importances_"):
        total = best_xgb.feature_importances_.sum()
        for feat, imp in zip(feature_cols, best_xgb.feature_importances_):
            importances[feat] = round(float(imp / total) * 100, 1) if total > 0 else 0.0

    full_grid = [
        {
            "position": int(row["predicted_pos"]),
            "driver": row["driver"],
            "team": row["team"],
            "podiumProb": round(float(row["podium_prob"]) * 100, 1),
            "gridPosition": int(BRITISH_QUALIFYING_GRID.get(row["driver"], 0)) if QUALIFYING_DONE else None,
            "sprintPosition": int(BRITISH_SPRINT_RESULTS.get(row["driver"], 0)),
        }
        for _, row in british_df.iterrows()
    ]
    return full_grid, importances


# =============================================================================
# SECTION 8 — SAVE JSON
# =============================================================================

def save_json(full_grid, importances, feature_cols, xgb_f1, lgbm_f1, quali_used, race_pace_used):
    podium = full_grid[:3]
    winner_model = "XGBClassifier" if xgb_f1 >= lgbm_f1 else "LGBMClassifier"

    output = {
        "slug": "british-grand-prix",
        "raceName": RACE_NAME,
        "round": ROUND_NUMBER,
        "circuit": CIRCUIT,
        "date": RACE_DATE,
        "status": "Final Prediction",
        "qualifyingDone": QUALIFYING_DONE,
        "sprintWeekend": IS_SPRINT,
        "modelUsed": (
            f"CalibratedClassifierCV (StratifiedKFold5) -> VotingClassifier "
            f"(XGBClassifier [Optuna] + LGBMClassifier [Optuna]) "
            f"+ smooth grid floor P{GRID_FLOOR_CUTOFF}+"
        ),
        "predictedPodium": [
            {"pos": p["position"], "driver": p["driver"], "team": p["team"], "confidence": p["podiumProb"]}
            for p in podium
        ],
        "fullGrid": full_grid,
        "features": feature_cols,
        "featureImportances": importances,
        "modelMetrics": {
            "cvFolds": CV_FOLDS,
            "cvScoring": CV_SCORING,
            "calibration": "CalibratedClassifierCV sigmoid, StratifiedKFold(5)",
            "gridFloor": f"P{GRID_FLOOR_CUTOFF}+ -> exponential decay (rate={GRID_FLOOR_DECAY})",
            "tuning": {
                "XGBClassifier": {"method": f"Optuna {N_OPTUNA} trials", "cv_f1": xgb_f1},
                "LGBMClassifier": {"method": f"Optuna {N_OPTUNA} trials", "cv_f1": lgbm_f1},
                "winner": winner_model,
            },
        },
        "trainingData": {
            "races": ["Australia", "China", "Japan", "Miami", "Canada", "Monaco", "Barcelona", "Austria"],
            "rows": TOTAL_RACES * 22,
        },
        "sprintResults": BRITISH_SPRINT_RESULTS,
        "actualResult": {"P1": "", "P2": "", "P3": ""},
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved -> {OUTPUT_FILE}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    feature_cols = get_feature_cols()

    quali_deltas = load_quali_delta()
    quali_used = len(quali_deltas) > 0
    race_pace_deltas = load_race_pace_proxy()
    race_pace_used = len(race_pace_deltas) > 0

    race_df = compute_race_features()
    race_df = add_rolling_features(race_df)

    X_train = race_df[feature_cols].values
    y_train = race_df["podium"].values

    best_xgb, xgb_f1 = tune_xgb(X_train, y_train)
    best_lgbm, lgbm_f1 = tune_lgbm(X_train, y_train)

    voting_clf = VotingClassifier(
        estimators=[("xgb", best_xgb), ("lgbm", best_lgbm)],
        voting="soft",
    )
    voting_clf.fit(X_train, y_train)

    british_df = build_british_rows(race_df, quali_deltas, race_pace_deltas)
    full_grid, importances = predict_british(voting_clf, best_xgb, british_df, X_train, y_train)

    print("\nBRITISH GP 2026 -- FINAL PREDICTION")
    for entry in full_grid[:3]:
        print(f"  P{entry['position']}  {entry['driver']:<6}  {entry['team']:<28}  {entry['podiumProb']}%  [Q{entry['gridPosition']} S{entry['sprintPosition']}]")

    print("\nFeature importances (XGBClassifier):")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"    {feat:<30} {imp:.1f}%")

    save_json(full_grid, importances, feature_cols, xgb_f1, lgbm_f1, quali_used, race_pace_used)


if __name__ == "__main__":
    main()
