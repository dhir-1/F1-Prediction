"""
barcelona_prediction.py — Dhir's Pit Wall · Round 7 · Barcelona-Catalunya GP · June 14, 2026
==============================================================================================
Training data : 6 completed 2026 races (Australia, China, Japan, Miami, Canada, Monaco)
Features      : grid_position, grid_position_squared, avg_finish_last3, finish_trend,
                rolling_podium_rate, avg_lap_time_delta, tyre_consistency,
                constructor_avg_finish, dnf_rate, high_speed_circuit_avg_finish
Models        : XGBClassifier (Optuna) vs LGBMClassifier (GridSearchCV)
                → VotingClassifier (soft) → CalibratedClassifierCV (sigmoid)
Tuning        : Optuna 60 trials for XGB · GridSearchCV exhaustive for LGBM · 5-fold CV
Data          : FastF1 for all lap times, results, Barcelona Q3 qualifying

WORKFLOW
--------
  Before qualifying : QUALIFYING_DONE=False, USE_GRID_POSITION=False
  After qualifying  : QUALIFYING_DONE=True,  USE_GRID_POSITION=True
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")


# =============================================================================
# SECTION 0 — SETTINGS
# =============================================================================

QUALIFYING_DONE   = True
USE_GRID_POSITION = True

ROUND_NUMBER = 7
RACE_NAME    = "Barcelona-Catalunya Grand Prix"
CIRCUIT      = "Circuit de Barcelona-Catalunya"
RACE_DATE    = "2026-06-14"

SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
CACHE_DIR   = BACKEND_DIR / "data" / "fastf1_cache"
OUTPUT_FILE = BACKEND_DIR / "data" / "predictions" / "barcelona-2026.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

TRAINING_RACES = [
    (2026, "Australia", "R"),
    (2026, "China",     "R"),
    (2026, "Japan",     "R"),
    (2026, "Miami",     "R"),
    (2026, "Canada",    "R"),
    (2026, "Monaco",    "R"),
]

HIGH_SPEED_RACES = {"Australian Grand Prix", "Japanese Grand Prix", "Chinese Grand Prix"}

BARCELONA_QUALIFYING_GRID = {
    "RUS": 1,
    "HAM": 2,
    "ANT": 3,
    "NOR": 4,
    "VER": 5,
    "HAD": 6,
    "PIA": 7,
    "LAW": 8,
    "HUL": 9,
    "LEC": 10,
    "LIN": 11,
    "BOR": 12,
    "COL": 13,
    "GAS": 14,
    "BEA": 15,
    "SAI": 16,
    "OCO": 17,
    "ALB": 18,
    "PER": 19,
    "BOT": 20,
    "STR": 21,
    "ALO": 22,
}

TOTAL_RACES  = len(TRAINING_RACES)
CV_FOLDS     = 5
CV_SCORING   = "f1"
N_OPTUNA     = 60
RANDOM_SEED  = 42


# =============================================================================
# SECTION 1 — FEATURE COLUMNS
# =============================================================================

_ALL_FEATURES = [
    "grid_position",                   # Barcelona qualifying position
    "grid_position_squared",           # exponential grid penalty — kills GAS P14 noise
    "avg_finish_last3",                # rolling 3-race avg finish position
    "finish_trend",                    # slope of last 3 finishes
    "rolling_podium_rate",             # podiums scored / races run (ANT=1.0, HAM=0.5)
    "avg_lap_time_delta",              # avg clean lap vs race winner — rolling 3
    "tyre_consistency",                # std-dev of clean lap times — lower = better
    "constructor_avg_finish",          # team expanding season avg finish
    "dnf_rate",                        # DNFs / races run — NOR/VER at 0.33
    "high_speed_circuit_avg_finish",   # avg finish at AUS + JPN + CHN only
]

def get_feature_cols():
    excluded = []
    if not USE_GRID_POSITION:
        excluded += ["grid_position", "grid_position_squared"]
    return [f for f in _ALL_FEATURES if f not in excluded]


# =============================================================================
# SECTION 2 — LOAD SESSIONS
# =============================================================================

def load_sessions():
    print(f"\n[1/6] Loading {len(TRAINING_RACES)} race sessions via FastF1...")
    sessions = []
    for year, race, stype in TRAINING_RACES:
        print(f"  -> {year} {race}...", end=" ", flush=True)
        sess = fastf1.get_session(year, race, stype)
        sess.load(laps=True, telemetry=False, weather=False, messages=False)
        sessions.append(sess)
        print(f"OK ({len(sess.results)} drivers)")
    print("  All sessions loaded")
    return sessions


def load_barcelona_quali_delta():
    if not QUALIFYING_DONE:
        print("\n[1b/6] Qualifying not done — using season rolling avg for lap delta")
        return {}

    print("\n[1b/6] Loading Barcelona Q3 qualifying lap time deltas...")
    quali_deltas = {}
    try:
        q_sess = fastf1.get_session(2026, ROUND_NUMBER, "Q")
        q_sess.load(laps=True, telemetry=False, weather=False, messages=False)
        results = q_sess.results

        q3_times = []
        for _, row in results.iterrows():
            t = row.get("Q3")
            if t is not None and pd.notna(t):
                t_sec = t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                q3_times.append(t_sec)
        pole_time = min(q3_times) if q3_times else None

        if pole_time is None:
            print("  WARNING: Could not determine pole time — using season avg")
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

        print(f"  Deltas loaded for {len(quali_deltas)} drivers | Pole: {pole_time:.3f}s")

    except Exception as exc:
        print(f"  WARNING: Qualifying load failed ({exc}) — using season avg")

    return quali_deltas


# =============================================================================
# SECTION 3 — COMPUTE PER-RACE FEATURES FROM FASTF1
# =============================================================================

def compute_race_features(sessions):
    print("\n[2/6] Computing per-race features from FastF1...")
    all_rows = []

    for sess_idx, sess in enumerate(sessions):
        results       = sess.results
        laps          = sess.laps
        race_name     = sess.event["EventName"]
        is_high_speed = int(race_name in HIGH_SPEED_RACES)

        winner_code    = results.sort_values("Position").iloc[0]["Abbreviation"]
        winner_laps    = laps.pick_drivers(winner_code).pick_quicklaps()
        winner_avg_lap = (
            winner_laps["LapTime"].dropna()
                        .apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t))
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

            drv_laps   = laps.pick_drivers(code)
            clean_laps = drv_laps.pick_quicklaps()

            if not clean_laps.empty and winner_avg_lap:
                lap_times = (
                    clean_laps["LapTime"].dropna()
                               .apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t))
                )
                avg_lap_time_delta = float(lap_times.mean()) - winner_avg_lap
                tyre_consistency   = float(lap_times.std()) if len(lap_times) >= 3 else 2.0
            else:
                avg_lap_time_delta = 2.0
                tyre_consistency   = 2.0

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
                "tyre_consistency":   tyre_consistency,
                "is_high_speed":      is_high_speed,
                "podium":             1 if finish_pos <= 3 else 0,
            })

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)
    print(f"  {len(df)} rows | {df['race'].nunique()} races | {df['driver'].nunique()} drivers")
    print(f"  Podium labels : {df['podium'].value_counts().to_dict()}")
    print(f"  DNF labels    : {df['is_dnf'].value_counts().to_dict()}")
    return df


# =============================================================================
# SECTION 4 — ROLLING & SEASON FEATURES
# =============================================================================

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


def add_rolling_features(df):
    print("\n[3/6] Adding rolling & season features...")
    df = df.copy().sort_values(["driver", "sess_idx"]).reset_index(drop=True)

    # avg_finish_last3 — rolling 3-race avg finish
    df["avg_finish_last3"] = (
        df.groupby("driver")["finish_position"]
          .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # finish_trend — linear slope of last 3 finishes
    df["finish_trend"] = (
        df.groupby("driver")["finish_position"]
          .transform(compute_trend)
    )

    # rolling_podium_rate — cumulative podiums / races run
    df["race_number"]        = df.groupby("driver").cumcount() + 1
    df["cumulative_podiums"] = df.groupby("driver")["podium"].transform(lambda x: x.cumsum())
    df["rolling_podium_rate"] = df["cumulative_podiums"] / df["race_number"]

    # avg_lap_time_delta — rolling 3-race mean
    df["avg_lap_time_delta"] = (
        df.groupby("driver")["avg_lap_time_delta"]
          .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # tyre_consistency — rolling 3-race mean of per-race std-dev
    df["tyre_consistency"] = (
        df.groupby("driver")["tyre_consistency"]
          .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # constructor_avg_finish — team expanding season mean
    df = df.sort_values(["team", "sess_idx"]).reset_index(drop=True)
    df["constructor_avg_finish"] = (
        df.groupby("team")["finish_position"]
          .transform(lambda x: x.expanding().mean())
    )
    df = df.sort_values(["driver", "sess_idx"]).reset_index(drop=True)

    # dnf_rate — cumulative DNFs / races run
    df["dnf_count"] = df.groupby("driver")["is_dnf"].transform(lambda x: x.cumsum())
    df["dnf_rate"]  = df["dnf_count"] / df["race_number"]

    # grid_position_squared — exponential grid penalty for training rows
    df["grid_position_squared"] = df["grid_position"] ** 2

    # high_speed_circuit_avg_finish — AUS + JPN + CHN only, carry forward
    def high_speed_avg(grp):
        result  = pd.Series(index=grp.index, dtype=float)
        running = []
        for idx, row in grp.iterrows():
            if row["is_high_speed"]:
                running.append(row["finish_position"])
            result[idx] = float(np.mean(running)) if running else float(grp["finish_position"].mean())
        return result

    df["high_speed_circuit_avg_finish"] = (
        df.groupby("driver", group_keys=False).apply(high_speed_avg)
    )

    print(f"  Features computed for {df['driver'].nunique()} drivers")
    return df


# =============================================================================
# SECTION 5 — TUNING: OPTUNA (XGB) vs GRIDSEARCHCV (LGBM)
# =============================================================================

def tune_xgb_optuna(X, y):
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    spw   = n_neg / n_pos if n_pos > 0 else 1.0
    cv    = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    def objective(trial):
        m = XGBClassifier(
            n_estimators=     trial.suggest_int("n_estimators", 50, 300),
            max_depth=        trial.suggest_int("max_depth", 2, 4),
            learning_rate=    trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample=        trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree= trial.suggest_float("colsample_bytree", 0.6, 1.0),
            reg_lambda=       trial.suggest_float("reg_lambda", 1.0, 15.0),
            reg_alpha=        trial.suggest_float("reg_alpha", 0.0, 5.0),
            min_child_weight= trial.suggest_int("min_child_weight", 1, 5),
            scale_pos_weight= spw,
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
            random_state=RANDOM_SEED,
        )
        scores = cross_val_score(m, X, y, cv=cv, scoring=CV_SCORING)
        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=N_OPTUNA)

    best = XGBClassifier(
        **study.best_params,
        scale_pos_weight=spw,
        use_label_encoder=False,
        eval_metric="logloss",
        verbosity=0,
        random_state=RANDOM_SEED,
    )
    best.fit(X, y)
    return best, round(study.best_value, 4)


def tune_lgbm_gridsearch(X, y):
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    param_grid = {
        "n_estimators":  [50, 100, 200],
        "max_depth":     [2, 3, 4],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "num_leaves":    [7, 15, 31],
        "reg_lambda":    [0.5, 2.0, 5.0],
    }
    base = LGBMClassifier(class_weight="balanced", subsample=0.8, random_state=RANDOM_SEED, verbose=-1)
    gs   = GridSearchCV(base, param_grid, cv=cv, scoring=CV_SCORING, n_jobs=-1, refit=True)
    gs.fit(X, y)
    return gs.best_estimator_, round(float(gs.best_score_), 4)


# =============================================================================
# SECTION 6 — BUILD BARCELONA INFERENCE ROWS
# =============================================================================

def build_barcelona_rows(df, sessions, quali_deltas):
    feature_cols = get_feature_cols()
    last_sess    = sessions[-1]  # Monaco — last completed race
    all_drivers  = last_sess.results
    rows = []

    for _, driver in all_drivers.iterrows():
        code = str(driver["Abbreviation"]).strip().upper()
        team = str(driver.get("TeamName", "Unknown"))

        drv_history = df[df["driver"] == code].sort_values("sess_idx")
        if drv_history.empty:
            row = {feat: 0.0 for feat in feature_cols}
            row.update({"driver": code, "team": team})
            rows.append(row)
            continue

        last      = drv_history.iloc[-1]
        grid_pos  = float(BARCELONA_QUALIFYING_GRID.get(code, 11.0)) if (USE_GRID_POSITION and QUALIFYING_DONE) else 11.0
        lap_delta = quali_deltas.get(code, float(last["avg_lap_time_delta"]))

        row = {
            "driver":                        code,
            "team":                          team,
            "grid_position":                 grid_pos,
            "grid_position_squared":         grid_pos ** 2,
            "avg_finish_last3":              float(last["avg_finish_last3"]),
            "finish_trend":                  float(last["finish_trend"]),
            "rolling_podium_rate":           float(last["rolling_podium_rate"]),
            "avg_lap_time_delta":            lap_delta,
            "tyre_consistency":              float(last["tyre_consistency"]),
            "constructor_avg_finish":        float(last["constructor_avg_finish"]),
            "dnf_rate":                      float(last["dnf_rate"]),
            "high_speed_circuit_avg_finish": float(last["high_speed_circuit_avg_finish"]),
        }
        rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 7 — PREDICT & RANK
# =============================================================================

def predict_barcelona(voting_clf, best_xgb, barcelona_df, X_train, y_train):
    feature_cols = get_feature_cols()
    X_barcelona  = barcelona_df[feature_cols].fillna(0).values

    print("  Calibrating ensemble (sigmoid, prefit)...")
    calibrated = CalibratedClassifierCV(estimator=voting_clf, method="sigmoid", cv=None)
    calibrated.fit(X_train, y_train)

    probs                         = calibrated.predict_proba(X_barcelona)[:, 1]
    barcelona_df                  = barcelona_df.copy()
    barcelona_df["podium_prob"]   = probs
    barcelona_df                  = barcelona_df.sort_values("podium_prob", ascending=False).reset_index(drop=True)
    barcelona_df["predicted_pos"] = barcelona_df.index + 1

    importances = {}
    if hasattr(best_xgb, "feature_importances_"):
        total = best_xgb.feature_importances_.sum()
        for feat, imp in zip(feature_cols, best_xgb.feature_importances_):
            importances[feat] = round(float(imp / total) * 100, 1) if total > 0 else 0.0

    grid_map  = BARCELONA_QUALIFYING_GRID if QUALIFYING_DONE else {}
    full_grid = [
        {
            "position":     int(row["predicted_pos"]),
            "driver":       row["driver"],
            "team":         row["team"],
            "podiumProb":   round(float(row["podium_prob"]) * 100, 1),
            "gridPosition": int(grid_map.get(row["driver"], 0)) if QUALIFYING_DONE else None,
        }
        for _, row in barcelona_df.iterrows()
    ]
    return full_grid, importances


# =============================================================================
# SECTION 8 — SAVE JSON
# =============================================================================

def save_json(full_grid, importances, feature_cols, xgb_f1, lgbm_f1, winner_model, quali_used):
    podium = full_grid[:3]
    status = "Final Prediction" if QUALIFYING_DONE else "Pre-Qualifying Forecast"

    output = {
        "slug":           "barcelona-grand-prix",
        "raceName":       RACE_NAME,
        "round":          ROUND_NUMBER,
        "circuit":        CIRCUIT,
        "date":           RACE_DATE,
        "status":         status,
        "qualifyingDone": QUALIFYING_DONE,

        "modelUsed": (
            f"CalibratedClassifierCV -> VotingClassifier "
            f"(XGBClassifier [Optuna {N_OPTUNA} trials] + LGBMClassifier [GridSearchCV]) "
            f"-- {winner_model} led ensemble"
        ),

        "predictedPodium": [
            {"pos": p["position"], "driver": p["driver"], "team": p["team"], "confidence": p["podiumProb"]}
            for p in podium
        ],
        "fullGrid": full_grid,

        "features":           feature_cols,
        "featureImportances": importances,

        "modelMetrics": {
            "cvFolds":     CV_FOLDS,
            "cvScoring":   CV_SCORING,
            "calibration": "CalibratedClassifierCV sigmoid cv=None",
            "tuning": {
                "XGBClassifier":  {"method": f"Optuna {N_OPTUNA} trials", "cv_f1": xgb_f1},
                "LGBMClassifier": {"method": "GridSearchCV exhaustive",    "cv_f1": lgbm_f1},
                "winner": winner_model,
            },
        },

        "trainingData": {
            "races":    ["Australia", "China", "Japan", "Miami", "Canada", "Monaco"],
            "rows":     TOTAL_RACES * 22,
            "cvMethod": f"XGB: Optuna {N_OPTUNA} trials + LGBM: GridSearchCV + {CV_FOLDS}-fold + f1",
        },

        "actualResult": {"P1": "", "P2": "", "P3": ""},

        "pitWallNotes": [
            "Barcelona 2026: High-deg circuit -- C2/C3/C4, one step softer than usual.",
            "No DRS -- Straight Mode zones replace it on main straight and Turn 3 exit.",
            "grid_position_squared added -- exponentially penalises GAS P14 (196) vs RUS P1 (1).",
            "rolling_podium_rate: ANT=1.00, HAM=0.50, RUS=0.17, NOR=0.17 -- clean podium signal.",
            "dnf_rate: NOR and VER both at 0.33 (2 DNFs in 6 races) after Monaco retirements.",
            "high_speed_circuit_avg_finish filters Monaco + Canada -- only AUS, JPN, CHN counted.",
            "tyre_consistency = std-dev of clean laps -- front-left deg decisive at Barcelona.",
            f"avg_lap_time_delta: {'Barcelona Q3 qualifying' if quali_used else 'season rolling avg'}.",
            f"Tuning: XGB Optuna f1={xgb_f1:.4f} vs LGBM GridSearch f1={lgbm_f1:.4f} -- {winner_model} led.",
            "6 training races (132 rows) -- most data Pit Wall has had this season.",
        ],

        "limitations": [
            "132 training rows -- midfield P4-P8 probabilities will compress.",
            "high_speed_circuit_avg_finish based on only 3 races (AUS, JPN, CHN).",
            "No weather feature -- Barcelona June is deterministically sunny.",
            "rolling_podium_rate favours consistent winners -- may underrate one-off podium threats.",
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved -> {OUTPUT_FILE}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    feature_cols = get_feature_cols()
    print("=" * 68)
    print(f"  DHIR'S PIT WALL -- {RACE_NAME.upper()}")
    print(f"  Round {ROUND_NUMBER} | {CIRCUIT} | {RACE_DATE}")
    print(f"  Features : {len(feature_cols)} | USE_GRID_POSITION={USE_GRID_POSITION}")
    print(f"  Training : {len(TRAINING_RACES)} races ({TOTAL_RACES * 22} rows)")
    print("=" * 68)

    sessions     = load_sessions()
    quali_deltas = load_barcelona_quali_delta()
    quali_used   = len(quali_deltas) > 0

    race_df = compute_race_features(sessions)
    race_df = add_rolling_features(race_df)

    print(f"\n[4/6] Tuning -- XGB (Optuna {N_OPTUNA} trials) vs LGBM (GridSearchCV)")
    X_train = race_df[feature_cols].fillna(0).values
    y_train = race_df["podium"].values
    print(f"  Training shape : {X_train.shape} | Podium positives : {y_train.sum()}")

    print("\n-- XGBClassifier -> Optuna --")
    best_xgb, xgb_f1 = tune_xgb_optuna(X_train, y_train)
    print(f"  XGB best CV f1 = {xgb_f1:.4f}")

    print("\n-- LGBMClassifier -> GridSearchCV --")
    best_lgbm, lgbm_f1 = tune_lgbm_gridsearch(X_train, y_train)
    print(f"  LGBM best CV f1 = {lgbm_f1:.4f}")

    winner_model = "XGBClassifier" if xgb_f1 >= lgbm_f1 else "LGBMClassifier"
    print(f"\n  Winner: {winner_model} (XGB={xgb_f1:.4f} vs LGBM={lgbm_f1:.4f})")

    print("\n[5/6] Building VotingClassifier (soft) + Calibration...")
    voting_clf = VotingClassifier(
        estimators=[("xgb", best_xgb), ("lgbm", best_lgbm)],
        voting="soft",
    )
    voting_clf.fit(X_train, y_train)
    print("  Ensemble: XGBClassifier + LGBMClassifier")

    print(f"\n[6/6] Predicting Barcelona ({'POST-QUALIFYING' if QUALIFYING_DONE else 'PRE-QUALIFYING'})...")
    barcelona_df           = build_barcelona_rows(race_df, sessions, quali_deltas)
    full_grid, importances = predict_barcelona(voting_clf, best_xgb, barcelona_df, X_train, y_train)

    print("\n" + "=" * 68)
    print(f"  BARCELONA-CATALUNYA GP 2026 -- {'FINAL' if QUALIFYING_DONE else 'PRE-QUALIFYING'}")
    print("=" * 68)
    medals = {1: "P1", 2: "P2", 3: "P3"}
    for entry in full_grid[:3]:
        grid_str = f"  [Q{entry['gridPosition']}]" if entry["gridPosition"] else ""
        print(f"  {medals[entry['position']]}  {entry['driver']:<6}  {entry['team']:<28}  {entry['podiumProb']}%{grid_str}")

    print(f"\n  avg_lap_time_delta : {'Barcelona Q3' if quali_used else 'season rolling avg'}")
    print(f"  Tuning             : XGB={xgb_f1:.4f} | LGBM={lgbm_f1:.4f} | Winner={winner_model}")

    print("\n  Feature importances (XGBClassifier):")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        bar = "#" * int(imp / 2)
        print(f"    {feat:<35} {bar:<25} {imp:.1f}%")

    print("\n  Full top 10:")
    print(f"  {'POS':<5} {'DRV':<6} {'TEAM':<28} {'PROB':>6}  GRID")
    print("  " + "-" * 56)
    for entry in full_grid[:10]:
        grid_str = f"Q{entry['gridPosition']}" if entry["gridPosition"] else "--"
        print(f"  P{entry['position']:<4} {entry['driver']:<6} {entry['team']:<28} {entry['podiumProb']:>5.1f}%  [{grid_str}]")

    save_json(full_grid, importances, feature_cols, xgb_f1, lgbm_f1, winner_model, quali_used)

    print("\n  NEXT STEPS:")
    print("  1. After Sunday race -> fill actualResult in barcelona-2026.json")
    print("  2. Hit /clear-cache on backend to refresh dashboard")
    print("=" * 68)


if __name__ == "__main__":
    main()