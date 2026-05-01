# =============================================================================
# DHIR'S PIT WALL — F1 2026 RACE PREDICTION PIPELINE
# predict.py
#
# WHAT THIS FILE DOES (plain English):
#   1. Pulls real 2026 race data from FastF1 (Australia, China, Japan)
#   2. Builds a feature table — one row per driver per race (66 rows total)
#   3. Trains 3 models: XGBClassifier, XGBRegressor, Random Forest
#   4. Evaluates each model using Leave One Race Out (LORO) cross-validation
#   5. Picks the best model and makes a Miami GP podium prediction
#   6. Saves the prediction as backend/data/predictions/miami-2026.json
#
# HOW TO RUN:
#   Step 1 (once):  pip install fastf1 xgboost scikit-learn pandas numpy
#   Step 2:         python scripts/generate_prediction.py
#   Step 3 (May 3): Set QUALIFYING_DONE = True and fill MIAMI_GRID below,
#                   then run python scripts/generate_prediction.py again.
#
# =============================================================================

import fastf1
import pandas as pd
import numpy as np
import json
import warnings
import requests
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (f1_score, precision_score,
                             recall_score, roc_auc_score, mean_absolute_error)
from sklearn.preprocessing import label_binarize
from xgboost import XGBClassifier, XGBRegressor

from app.core.config import CACHE_DIR, MIAMI_PREDICTION_FILE

warnings.filterwarnings("ignore")


# =============================================================================
# SECTION 0 — SETTINGS YOU CONTROL
# =============================================================================

# FastF1 saves downloaded data to this folder so it doesn't re-download
# every time you run the script. Create this folder once if it doesn't exist.
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))
# In Section 0 — add this line, it never changes
MIAMI_STREET_CIRCUIT = 1  # Miami International Autodrome is a semi-permanent street circuit
# The 3 races we have data for in 2026.
# Format: (year, race_name_as_string, session_type)
TRAINING_RACES = [
    (2026, "Australia", "R"),
    (2026, "China",     "R"),
    (2026, "Japan",     "R"),
]

# ── MIAMI GRID POSITION ──────────────────────────────────────────────────────
# Before qualifying (May 3rd): QUALIFYING_DONE = False
#   → script uses each driver's average qualifying position from 2026 so far
#
# After qualifying (May 3rd evening): QUALIFYING_DONE = True
#   → fill in MIAMI_GRID below with real positions from qualifying results
#     Key = driver 3-letter code, Value = grid position (1 = pole)
# ─────────────────────────────────────────────────────────────────────────────
QUALIFYING_DONE = False   # <-- flip to True on May 3rd evening

MIAMI_GRID = {
    # Fill these in on May 3rd after qualifying.
    # Example format (replace with real results):
    # "HAM": 1,
    # "LEC": 2,
    # "NOR": 3,
    # ... all 20 drivers
}

#Check the weather of the miami race at 16:00

def fetch_miami_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=25.9581&longitude=-80.2389"
        "&hourly=temperature_2m,precipitation_probability,rain"
        "&timezone=America%2FNew_York"
        "&start_date=2026-05-04&end_date=2026-05-04"
    )

    response = requests.get(url)
    data = response.json()

    hour_index = 16

    rain_prob = data["hourly"]["precipitation_probability"][hour_index]
    track_temp = data["hourly"]["temperature_2m"][hour_index] + 10
    
    weather_wet = 1 if rain_prob >= 50 else 0

    print(f" Miami forecast at 16:00 ET:")
    print(f" Rain probability : {rain_prob}%")
    print(f" Estimated track temp : {track_temp}°C")
    print(f" Weather wet flag : {weather_wet}")

    return weather_wet, track_temp


# =============================================================================
# SECTION 1 — PULLING DATA FROM FASTF1
# =============================================================================
# FastF1 talks to the official F1 API and returns real telemetry, lap times,
# results, pit stop data, and weather. We load each race session one by one.

def load_race_session(year, race_name, session_type="R"):
    """
    Loads a single race session from FastF1.

    year        : e.g. 2026
    race_name   : e.g. "Australia"
    session_type: "R" = Race, "Q" = Qualifying

    Returns the session object (contains results, laps, weather, etc.)
    """
    print(f"  → Loading {year} {race_name} ({session_type})...")
    session = fastf1.get_session(year, race_name, session_type)

    # load() fetches:
    #   laps=True     → lap-by-lap data (needed for consistency + pit stops)
    #   telemetry=False → we don't need car sensor data, saves time
    #   weather=True  → track temp, rainfall etc.
    #   messages=False→ team radio, not needed
    session.load(laps=True, telemetry=False, weather=True, messages=False)
    return session


# =============================================================================
# SECTION 2 — BUILDING FEATURES FOR ONE RACE
# =============================================================================
# This is the heart of the pipeline. For each race, for each driver,
# we compute all 12 features. The result is one row per driver.
#
# IMPORTANT RULE: Every feature must be knowable BEFORE the race starts.
# We never use the finishing position as a feature — that's what we're
# predicting. We never use lap times FROM the race itself — only from
# past races.

def build_features_for_race(race_session, all_previous_sessions,
                             street_circuit, weather_wet, track_temp):
    """
    Builds the feature table for one race.

    race_session         : the session we're building features for
    all_previous_sessions: list of all sessions BEFORE this race
                           (used to compute rolling averages)
    street_circuit       : 1 if this circuit is a street/semi-permanent track
    weather_wet          : 1 if wet race, 0 if dry
    track_temp           : track temperature in Celsius

    Returns a pandas DataFrame — one row per driver, columns = features + target
    """

    results = race_session.results  # official finishing order
    laps    = race_session.laps     # all laps from this race

    rows = []

    for _, driver in results.iterrows():
        drv_code = driver["Abbreviation"]   # e.g. "HAM", "VER", "LEC"

        # ── FEATURE 1: Grid Position ────────────────────────────────────────
        # Where the driver started on the grid.
        # This is the single most predictive feature in F1.
        grid_pos = driver.get("GridPosition", np.nan)
        if pd.isna(grid_pos) or grid_pos == 0:
            grid_pos = driver.get("Position", 10)  # fallback if missing

        # ── FEATURE 2 & 3: Rolling form from previous races ─────────────────
        # avg_finish      : driver's average finishing position in 2026 so far
        # constructor_avg : team's average finishing position in 2026 so far
        # These tell us: is this driver/team "in form" right now?

        prev_finishes_driver      = []
        prev_finishes_constructor = []
        constructor = driver.get("TeamName", "Unknown")

        for prev_sess in all_previous_sessions:
            prev_results = prev_sess.results
            # Find this driver in the previous race
            drv_row = prev_results[prev_results["Abbreviation"] == drv_code]
            if not drv_row.empty:
                pos = drv_row.iloc[0].get("Position", np.nan)
                if not pd.isna(pos):
                    prev_finishes_driver.append(float(pos))

            # Find all drivers from the same team in the previous race
            team_rows = prev_results[prev_results["TeamName"] == constructor]
            for _, tr in team_rows.iterrows():
                pos = tr.get("Position", np.nan)
                if not pd.isna(pos):
                    prev_finishes_constructor.append(float(pos))

        # If no previous data, use 11 (midfield) as a neutral guess
        avg_finish      = np.mean(prev_finishes_driver)      if prev_finishes_driver      else 11.0
        constructor_avg = np.mean(prev_finishes_constructor) if prev_finishes_constructor else 11.0

        # ── FEATURE 4: Gap to Pole in Qualifying ────────────────────────────
        # How far behind pole position was this driver in qualifying?
        # Example: if pole was 1:17.000 and driver did 1:17.800, gap = 0.800s
        # This tells us raw one-lap car speed.
        # We get this from the race session's qualifying data (Q column in results).
        gap_to_pole = driver.get("Q3", np.nan)  # Q3 time for top drivers
        if pd.isna(gap_to_pole):
            gap_to_pole = driver.get("Q2", np.nan)
        if pd.isna(gap_to_pole):
            gap_to_pole = driver.get("Q1", np.nan)

        # FastF1 stores lap times as timedelta objects. Convert to seconds.
        if hasattr(gap_to_pole, "total_seconds"):
            gap_to_pole = gap_to_pole.total_seconds()

        # Now compute actual gap: driver's time minus the pole time
        # Pole time = minimum Q time among all drivers
        try:
            all_q_times = []
            for _, r in results.iterrows():
                t = r.get("Q3", np.nan) or r.get("Q2", np.nan) or r.get("Q1", np.nan)
                if hasattr(t, "total_seconds"):
                    all_q_times.append(t.total_seconds())
                elif not pd.isna(t):
                    all_q_times.append(float(t))
            pole_time = min(all_q_times) if all_q_times else np.nan
            gap_to_pole = (gap_to_pole - pole_time) if (not pd.isna(gap_to_pole) and not pd.isna(pole_time)) else 0.5
        except Exception:
            gap_to_pole = 0.5  # fallback: assume half-second gap

        # ── FEATURES 5 & 6: Pit Stop Stats ──────────────────────────────────
        # avg_pit_time   : how fast is the team at pit stops? (seconds)
        # avg_pit_count  : how many stops do they typically make?
        # Faster stops and correct strategy = competitive advantage.
        drv_laps = laps.pick_drivers(drv_code)

        # Get pit stop laps only (laps where PitInTime is not NaT)
        pit_laps = drv_laps[drv_laps["PitInTime"].notna()]
        avg_pit_count = len(pit_laps)

        # Pit stop duration = time from pit entry to pit exit
        pit_times = []
        for _, pl in pit_laps.iterrows():
            pit_in  = pl.get("PitInTime",  pd.NaT)
            pit_out = pl.get("PitOutTime", pd.NaT)
            if pd.notna(pit_in) and pd.notna(pit_out):
                duration = (pit_out - pit_in).total_seconds()
                if 0 < duration < 60:  # sanity check: valid pit stop range
                    pit_times.append(duration)

        avg_pit_time = np.mean(pit_times) if pit_times else 25.0  # fallback: 25s

        # ── FEATURE 7: Season Points ─────────────────────────────────────────
        # Total championship points scored so far. This captures consistency
        # because DNFs destroy points even if a driver is fast.
        season_points = 0.0
        for prev_sess in all_previous_sessions:
            prev_results = prev_sess.results
            drv_row = prev_results[prev_results["Abbreviation"] == drv_code]
            if not drv_row.empty:
                pts = drv_row.iloc[0].get("Points", 0)
                if not pd.isna(pts):
                    season_points += float(pts)

        # ── FEATURE 8: Lap Time Consistency (Std Dev) ────────────────────────
        # Standard deviation of lap times during the RACE.
        # Lower std dev = more consistent = better racecraft.
        # We use the previous races' std devs (not this race's, which would be cheating).
        consistency_values = []
        for prev_sess in all_previous_sessions:
            prev_laps = prev_sess.laps.pick_drivers(drv_code)
            # Filter: only proper racing laps (not safety car, in/out laps)
            clean_laps = prev_laps[
                (prev_laps["TrackStatus"] == "1") &
                (prev_laps["PitInTime"].isna()) &
                (prev_laps["PitOutTime"].isna())
            ]["LapTime"].dropna()
            if len(clean_laps) > 3:
                # Convert timedelta to seconds
                times_sec = clean_laps.apply(
                    lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                )
                consistency_values.append(times_sec.std())

        lap_consistency_std = np.mean(consistency_values) if consistency_values else 1.5

        # ── FEATURE 9: DNFs This Season ─────────────────────────────────────
        # How many times did this driver fail to finish a race?
        # A driver with 2 DNFs in 3 races is unreliable — lower predicted finish.
        # FastF1 marks DNFs with Status != "Finished" and not a lapped position.
        dnf_count = 0
        for prev_sess in all_previous_sessions:
            prev_results = prev_sess.results
            drv_row = prev_results[prev_results["Abbreviation"] == drv_code]
            if not drv_row.empty:
                status = str(drv_row.iloc[0].get("Status", ""))
                # Common DNF statuses: "Accident", "Engine", "Collision", "Retired"
                if status not in ("Finished",) and "Lap" not in status and "+" not in status:
                    dnf_count += 1

        # ── FEATURES 10–12: Circuit / Conditions ────────────────────────────
        # These come in as arguments — same value for all drivers in this race.
        # street_circuit  : 1 = street/semi-permanent (like Miami, Monaco)
        # weather_wet     : 1 = wet race (wet races shuffle the grid drastically)
        # track_temp      : affects tyre deg and pit strategy

        # ── New Regs flag ────────────────────────────────────────────────────
        # From Miami onwards, new energy management rules apply.
        # 0 for the 3 training races. 1 for Miami.
        # This is NOT a feature we compute — we set it manually.
        new_regs = 0   # training races ran under old regs

        # ── TARGET VARIABLE: Finishing Position ─────────────────────────────
        # This is what we're trying to predict.
        # 1 = winner, 2 = second, etc.
        finish_pos = driver.get("Position", np.nan)
        if hasattr(finish_pos, "item"):
            finish_pos = finish_pos.item()
        finish_pos = float(finish_pos) if not pd.isna(finish_pos) else 20.0

        # Also create a binary podium label (1 = top 3, 0 = outside top 3)
        podium = 1 if finish_pos <= 3 else 0

        rows.append({
            "driver":            drv_code,
            "team":              constructor,
            "race":              race_session.event["EventName"],
            # ── 12 Features ──
            "grid_position":         float(grid_pos),
            "avg_finish_last3":      avg_finish,
            "constructor_avg_finish":constructor_avg,
            "gap_to_pole":           gap_to_pole,
            "avg_pit_time":          avg_pit_time,
            "avg_pit_count":         float(avg_pit_count),
            "season_points":         season_points,
            "lap_consistency_std":   lap_consistency_std,
            "dnf_count":             float(dnf_count),
            "street_circuit":        float(street_circuit),
            "weather_wet":           float(weather_wet),
            "track_temp":            float(track_temp),
            "new_regs":              float(new_regs),
            # ── Targets ──
            "finish_position":       finish_pos,
            "podium":                podium,
        })

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 3 — LEAVE ONE RACE OUT (LORO) CROSS-VALIDATION
# =============================================================================
# With only 3 races of data we can't afford a normal train/test split.
# LORO works like this:
#
#   Round 1: Train on China + Japan → Predict Australia → Score
#   Round 2: Train on Australia + Japan → Predict China → Score
#   Round 3: Train on Australia + China → Predict Japan → Score
#
# Then we average the 3 scores. This gives us a realistic estimate of
# how well the model would do on a race it has never seen before — which
# is exactly what Miami is.

FEATURE_COLS = [
    "grid_position",
    "avg_finish_last3",
    "constructor_avg_finish",
    "gap_to_pole",
    "avg_pit_time",
    "avg_pit_count",
    "season_points",
    "lap_consistency_std",
    "dnf_count",
    "street_circuit",
    "weather_wet",
    "track_temp",
    "new_regs",
]


def loro_evaluate(full_df, race_names):
    """
    Runs LORO cross-validation across the 3 training races.

    full_df    : the full 66-row feature table
    race_names : list of race name strings (must match the 'race' column)

    Returns a dict of average scores across all 3 folds for each model.
    """

    results_log = {
        "XGBClassifier":        {"f1": [], "precision": [], "recall": [], "roc_auc": []},
        "XGBRegressor":         {"mae": []},
        "RandomForest":         {"f1": [], "precision": [], "recall": [], "roc_auc": []},
    }

    print("\n── LORO Cross-Validation ───────────────────────────────────────")

    for test_race in race_names:
        # Split: test on this race, train on everything else
        test_df  = full_df[full_df["race"] == test_race]
        train_df = full_df[full_df["race"] != test_race]

        X_train = train_df[FEATURE_COLS].values
        X_test  = test_df[FEATURE_COLS].values

        y_train_cls = train_df["podium"].values          # 1/0 for classifier
        y_test_cls  = test_df["podium"].values
        y_train_reg = train_df["finish_position"].values # 1–22 for regressor
        y_test_reg  = test_df["finish_position"].values

        print(f"\n  Fold: Train on all EXCEPT {test_race} → Test on {test_race}")
        print(f"  Train size: {len(train_df)} rows | Test size: {len(test_df)} rows")

        # ── XGBClassifier ────────────────────────────────────────────────────
        # scale_pos_weight tells XGBoost: "podium=1 is rare, weight it higher"
        # ratio = non-podium count / podium count
        n_nonpodium = (y_train_cls == 0).sum()
        n_podium    = (y_train_cls == 1).sum()
        spw = n_nonpodium / n_podium if n_podium > 0 else 1.0

        xgb_cls = XGBClassifier(
            n_estimators=50,       # number of trees — kept low to avoid overfitting on 44 rows
            max_depth=3,           # shallow trees = less overfitting
            learning_rate=0.1,
            subsample=0.8,         # use 80% of rows per tree
            colsample_bytree=0.8,  # use 80% of features per tree
            scale_pos_weight=spw,
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
            random_state=42,
        )
        xgb_cls.fit(X_train, y_train_cls)
        y_pred_cls  = xgb_cls.predict(X_test)
        y_prob_cls  = xgb_cls.predict_proba(X_test)[:, 1]  # probability of podium

        f1  = f1_score(y_test_cls, y_pred_cls, zero_division=0)
        pr  = precision_score(y_test_cls, y_pred_cls, zero_division=0)
        rc  = recall_score(y_test_cls, y_pred_cls, zero_division=0)
        try:
            auc = roc_auc_score(y_test_cls, y_prob_cls)
        except ValueError:
            auc = 0.5  # if only one class in test fold

        results_log["XGBClassifier"]["f1"].append(f1)
        results_log["XGBClassifier"]["precision"].append(pr)
        results_log["XGBClassifier"]["recall"].append(rc)
        results_log["XGBClassifier"]["roc_auc"].append(auc)
        print(f"  XGBClassifier → F1={f1:.3f}  P={pr:.3f}  R={rc:.3f}  AUC={auc:.3f}")

        # ── XGBRegressor ─────────────────────────────────────────────────────
        # Predicts finish position as a number (1.0 to 22.0).
        # Lower predicted value = higher expected finish.
        xgb_reg = XGBRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            verbosity=0,
            random_state=42,
        )
        xgb_reg.fit(X_train, y_train_reg)
        y_pred_reg = xgb_reg.predict(X_test)
        mae = mean_absolute_error(y_test_reg, y_pred_reg)

        results_log["XGBRegressor"]["mae"].append(mae)
        print(f"  XGBRegressor  → MAE={mae:.3f} positions")

        # ── Random Forest Classifier (baseline) ─────────────────────────────
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=4,
            class_weight="balanced",  # handles imbalance automatically
            random_state=42,
        )
        rf.fit(X_train, y_train_cls)
        y_pred_rf  = rf.predict(X_test)
        y_prob_rf  = rf.predict_proba(X_test)[:, 1]

        f1_rf  = f1_score(y_test_cls, y_pred_rf, zero_division=0)
        pr_rf  = precision_score(y_test_cls, y_pred_rf, zero_division=0)
        rc_rf  = recall_score(y_test_cls, y_pred_rf, zero_division=0)
        try:
            auc_rf = roc_auc_score(y_test_cls, y_prob_rf)
        except ValueError:
            auc_rf = 0.5

        results_log["RandomForest"]["f1"].append(f1_rf)
        results_log["RandomForest"]["precision"].append(pr_rf)
        results_log["RandomForest"]["recall"].append(rc_rf)
        results_log["RandomForest"]["roc_auc"].append(auc_rf)
        print(f"  RandomForest  → F1={f1_rf:.3f}  P={pr_rf:.3f}  R={rc_rf:.3f}  AUC={auc_rf:.3f}")

    # Compute averages across all 3 folds
    print("\n── Average Scores Across All Folds ────────────────────────────")
    avg_scores = {}
    for model_name, scores in results_log.items():
        avg_scores[model_name] = {k: round(float(np.mean(v)), 3) for k, v in scores.items()}
        print(f"  {model_name}: {avg_scores[model_name]}")

    return avg_scores


def pick_best_model(avg_scores):
    """
    Decides which model to use for the final prediction.

    Logic:
    - XGBClassifier and RandomForest: we compare by F1 score (primary metric)
    - XGBRegressor: if MAE < 3.5 positions, it's competitive
    - The model with highest F1, or lowest MAE if regressor wins, is chosen.
    """
    xgb_cls_f1 = avg_scores["XGBClassifier"].get("f1", 0)
    rf_f1       = avg_scores["RandomForest"].get("f1", 0)
    reg_mae     = avg_scores["XGBRegressor"].get("mae", 99)

    # Convert MAE to a comparable "score" (lower MAE = better)
    # A MAE of 0 = perfect, 3 = decent for 22-driver field
    reg_score = max(0, 1 - (reg_mae / 11))  # normalise to 0–1 scale

    best_score = max(xgb_cls_f1, rf_f1, reg_score)

    if best_score == xgb_cls_f1:
        return "XGBClassifier"
    elif best_score == rf_f1:
        return "RandomForest"
    else:
        return "XGBRegressor"


# =============================================================================
# SECTION 4 — BUILDING MIAMI PREDICTION FEATURES
# =============================================================================
# Miami hasn't happened yet, so we construct features manually using
# everything we know BEFORE the race.

def build_miami_features(training_sessions, all_sessions_combined_df, weather_wet, track_temp):
    """
    Builds the feature row for each driver for Miami GP.

    Since Miami hasn't been raced yet:
    - Grid position comes from MIAMI_GRID if QUALIFYING_DONE=True,
      otherwise we estimate using average 2026 qualifying position.
    - Rolling stats come from Australia + China + Japan.
    - Circuit/weather flags are set manually at the top of this file.

    Returns a DataFrame — one row per driver, same columns as training data.
    """

    # Get full driver list from the most recent race
    latest_session = training_sessions[-1]
    all_drivers    = list(latest_session.results["Abbreviation"])

    # Build a lookup: driver → average qualifying position across 2026
    # Used when QUALIFYING_DONE = False
    avg_quali_position = {}
    for sess in training_sessions:
        for _, drv in sess.results.iterrows():
            code = drv["Abbreviation"]
            grid = drv.get("GridPosition", np.nan)
            if not pd.isna(grid) and float(grid) > 0:
                avg_quali_position.setdefault(code, []).append(float(grid))

    avg_quali_est = {
        code: np.mean(vals) for code, vals in avg_quali_position.items()
    }

    rows = []
    for drv_code in all_drivers:

        # ── Grid Position ────────────────────────────────────────────────────
        if QUALIFYING_DONE and drv_code in MIAMI_GRID:
            grid_pos = float(MIAMI_GRID[drv_code])
            grid_source = "REAL qualifying"
        else:
            grid_pos = avg_quali_est.get(drv_code, 11.0)  # fallback: midfield
            grid_source = "ESTIMATED (avg 2026 quali)"

        # ── Rolling form (all 3 training races = "previous" races for Miami) ─
        prev_finishes_driver      = []
        prev_finishes_constructor = []

        # Get this driver's team from the last race
        drv_row = latest_session.results[
            latest_session.results["Abbreviation"] == drv_code
        ]
        constructor = drv_row.iloc[0]["TeamName"] if not drv_row.empty else "Unknown"

        for sess in training_sessions:
            res = sess.results
            d = res[res["Abbreviation"] == drv_code]
            if not d.empty:
                pos = d.iloc[0].get("Position", np.nan)
                if not pd.isna(pos):
                    prev_finishes_driver.append(float(pos))
            t = res[res["TeamName"] == constructor]
            for _, tr in t.iterrows():
                pos = tr.get("Position", np.nan)
                if not pd.isna(pos):
                    prev_finishes_constructor.append(float(pos))

        avg_finish      = np.mean(prev_finishes_driver)      if prev_finishes_driver      else 11.0
        constructor_avg = np.mean(prev_finishes_constructor) if prev_finishes_constructor else 11.0

        # ── Gap to pole: use average from 2026 season ────────────────────────
        gaps = []
        for sess in training_sessions:
            res = sess.results
            # Get all qualifying times in this session
            all_q = []
            for _, r in res.iterrows():
                t = r.get("Q3", np.nan) or r.get("Q2", np.nan) or r.get("Q1", np.nan)
                if hasattr(t, "total_seconds"):
                    all_q.append(t.total_seconds())
            if not all_q:
                continue
            pole_t = min(all_q)
            d = res[res["Abbreviation"] == drv_code]
            if not d.empty:
                t = d.iloc[0].get("Q3", np.nan) or d.iloc[0].get("Q2", np.nan) or d.iloc[0].get("Q1", np.nan)
                if hasattr(t, "total_seconds"):
                    gaps.append(t.total_seconds() - pole_t)

        gap_to_pole = np.mean(gaps) if gaps else 0.5

        # ── Pit stop stats: average across training races ─────────────────────
        pit_counts = []
        pit_times  = []
        for sess in training_sessions:
            sess_laps   = sess.laps.pick_drivers(drv_code)
            pit_laps_d  = sess_laps[sess_laps["PitInTime"].notna()]
            pit_counts.append(len(pit_laps_d))
            for _, pl in pit_laps_d.iterrows():
                pit_in  = pl.get("PitInTime",  pd.NaT)
                pit_out = pl.get("PitOutTime", pd.NaT)
                if pd.notna(pit_in) and pd.notna(pit_out):
                    dur = (pit_out - pit_in).total_seconds()
                    if 0 < dur < 60:
                        pit_times.append(dur)

        avg_pit_count = np.mean(pit_counts) if pit_counts else 1.5
        avg_pit_time  = np.mean(pit_times)  if pit_times  else 25.0

        # ── Season points (sum of all 3 races) ────────────────────────────────
        season_points = 0.0
        for sess in training_sessions:
            res = sess.results
            d = res[res["Abbreviation"] == drv_code]
            if not d.empty:
                pts = d.iloc[0].get("Points", 0)
                if not pd.isna(pts):
                    season_points += float(pts)

        # ── Lap consistency (std dev, average across training races) ──────────
        consistency_vals = []
        for sess in training_sessions:
            sess_laps = sess.laps.pick_drivers(drv_code)
            clean = sess_laps[
                (sess_laps["TrackStatus"] == "1") &
                (sess_laps["PitInTime"].isna()) &
                (sess_laps["PitOutTime"].isna())
            ]["LapTime"].dropna()
            if len(clean) > 3:
                times_sec = clean.apply(
                    lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t)
                )
                consistency_vals.append(times_sec.std())
        lap_consistency_std = np.mean(consistency_vals) if consistency_vals else 1.5

        # ── DNFs ──────────────────────────────────────────────────────────────
        dnf_count = 0
        for sess in training_sessions:
            res = sess.results
            d = res[res["Abbreviation"] == drv_code]
            if not d.empty:
                status = str(d.iloc[0].get("Status", ""))
                if status not in ("Finished",) and "Lap" not in status and "+" not in status:
                    dnf_count += 1

        rows.append({
            "driver":               drv_code,
            "team":                 constructor,
            "grid_source":          grid_source,
            "grid_position":        grid_pos,
            "avg_finish_last3":     avg_finish,
            "constructor_avg_finish": constructor_avg,
            "gap_to_pole":          gap_to_pole,
            "avg_pit_time":         avg_pit_time,
            "avg_pit_count":        float(avg_pit_count),
            "season_points":        season_points,
            "lap_consistency_std":  lap_consistency_std,
            "dnf_count":            float(dnf_count),
            "street_circuit":       float(MIAMI_STREET_CIRCUIT),
            "weather_wet":          float(weather_wet),
            "track_temp":           float(track_temp),  
            "new_regs":             1.0,   # Miami = first race under new regs
        })

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 5 — MAKE THE PREDICTION & SAVE JSON
# =============================================================================

def make_prediction(best_model_name, full_train_df, miami_df):
    """
    Trains the best model on ALL training data (not just 2 races — full 66 rows)
    and predicts for Miami.

    Returns a list of dicts: [{ driver, team, predicted_position, podium_prob }, ...]
    sorted from P1 (winner) to P20.
    """

    X_train = full_train_df[FEATURE_COLS].values
    X_miami = miami_df[FEATURE_COLS].values

    y_train_cls = full_train_df["podium"].values
    y_train_reg = full_train_df["finish_position"].values

    n_nonpodium = (y_train_cls == 0).sum()
    n_podium    = (y_train_cls == 1).sum()
    spw = n_nonpodium / n_podium if n_podium > 0 else 1.0

    if best_model_name == "XGBClassifier":
        model = XGBClassifier(
            n_estimators=50, max_depth=3, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=spw, use_label_encoder=False,
            eval_metric="logloss", verbosity=0, random_state=42,
        )
        model.fit(X_train, y_train_cls)
        podium_probs = model.predict_proba(X_miami)[:, 1]
        # Sort by podium probability descending → higher prob = predicted higher finish
        order = np.argsort(-podium_probs)
        predicted_positions = {miami_df.iloc[i]["driver"]: rank + 1
                                for rank, i in enumerate(order)}
        podium_prob_map = {miami_df.iloc[i]["driver"]: float(podium_probs[i])
                           for i in range(len(miami_df))}

    elif best_model_name == "XGBRegressor":
        model = XGBRegressor(
            n_estimators=50, max_depth=3, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            verbosity=0, random_state=42,
        )
        model.fit(X_train, y_train_reg)
        pred_positions_raw = model.predict(X_miami)
        order = np.argsort(pred_positions_raw)  # ascending: lowest = winner
        predicted_positions = {miami_df.iloc[i]["driver"]: rank + 1
                                for rank, i in enumerate(order)}
        # Convert predicted position to rough podium probability
        podium_prob_map = {
            miami_df.iloc[i]["driver"]: max(0, 1 - (pred_positions_raw[i] / 22))
            for i in range(len(miami_df))
        }

    else:  # RandomForest
        model = RandomForestClassifier(
            n_estimators=100, max_depth=4,
            class_weight="balanced", random_state=42,
        )
        model.fit(X_train, y_train_cls)
        podium_probs = model.predict_proba(X_miami)[:, 1]
        order = np.argsort(-podium_probs)
        predicted_positions = {miami_df.iloc[i]["driver"]: rank + 1
                                for rank, i in enumerate(order)}
        podium_prob_map = {miami_df.iloc[i]["driver"]: float(podium_probs[i])
                           for i in range(len(miami_df))}

    # ── Feature importances ────────────────────────────────────────────────
    # This tells us WHICH features mattered most for this prediction.
    # Useful for the model transparency section on the website.
    importances = {}
    if hasattr(model, "feature_importances_"):
        for feat, imp in zip(FEATURE_COLS, model.feature_importances_):
            importances[feat] = round(float(imp), 4)

    # ── Assemble final results ────────────────────────────────────────────
    all_preds = []
    for _, row in miami_df.iterrows():
        drv = row["driver"]
        all_preds.append({
            "position":      predicted_positions.get(drv, 20),
            "driver":        drv,
            "team":          row["team"],
            "podium_prob":   round(podium_prob_map.get(drv, 0.0) * 100, 1),  # as %
            "grid_position": int(row["grid_position"]),
            "grid_source":   row.get("grid_source", "estimated"),
        })

    all_preds.sort(key=lambda x: x["position"])
    return all_preds, importances


# =============================================================================
# SECTION 6 — SAVE JSON OUTPUT (for the React frontend)
# =============================================================================

def save_prediction_json(all_preds, best_model_name, avg_scores, importances):
    """
    Saves the prediction to a JSON file.

    The React frontend reads this file to render the prediction page.
    Schema matches the data structure defined in the project plan.
    """

    prediction_status = "Final Prediction" if QUALIFYING_DONE else "Pre-Qualifying Forecast"
    podium = all_preds[:3]

    output = {
        "raceName":       "Miami Grand Prix",
        "round":          6,
        "circuit":        "Miami International Autodrome",
        "date":           "2026-05-04",
        "status":         prediction_status,

        "predictedPodium": [
            {
                "pos":        p["position"],
                "driver":     p["driver"],
                "team":       p["team"],
                "confidence": p["podium_prob"],
            }
            for p in podium
        ],

        "fullGrid": all_preds,

        "modelUsed":    best_model_name,
        "features":     FEATURE_COLS,
        "featureImportances": importances,

        "metrics": avg_scores.get(best_model_name, {}),

        "trainingData": {
            "races":   ["Australia", "China", "Japan"],
            "rows":    66,
            "cvMethod": "Leave One Race Out (LORO)",
        },

        "limitations": [
            "Only 66 training rows (3 races x 22 drivers) — model may overfit.",
            "Miami runs under new energy management regulations (new_regs=1 flag added).",
            "No historical Miami-specific performance data used.",
            "Pre-qualifying: grid position is estimated, not real." if not QUALIFYING_DONE else
            "Grid position from real qualifying results.",
            "Cadillac and new teams may have incomplete FastF1 data.",
        ],

        "qualifying_done": QUALIFYING_DONE,
    }

    output_path = Path(MIAMI_PREDICTION_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n  ✓ Saved to {output_path}")
    return output_path


# =============================================================================
# MAIN — runs everything in order
# =============================================================================

def main():
    print("=" * 65)
    print("  DHIR'S PIT WALL — F1 2026 Miami GP Prediction")
    print("=" * 65)

    # ── STEP 1: Load all training race sessions ───────────────────────────
    print("\n[1/5] Loading training race data from FastF1...")
    training_sessions = []
    for year, race, stype in TRAINING_RACES:
        sess = load_race_session(year, race, stype)
        training_sessions.append(sess)
    print(f"  ✓ Loaded {len(training_sessions)} sessions")

    # ── STEP 2: Build feature table for each race ─────────────────────────
    # For race N, "previous sessions" = sessions 0..N-1
    print("\n[2/5] Building feature tables...")
    race_dfs = []

    # Australia (Round 1): no previous races → empty list
    df_aus = build_features_for_race(
        race_session=training_sessions[0],
        all_previous_sessions=[],
        street_circuit=0,   # Melbourne = permanent circuit
        weather_wet=0,
        track_temp=32.0,
    )
    race_dfs.append(df_aus)

    # China (Round 2): previous = Australia
    df_chn = build_features_for_race(
        race_session=training_sessions[1],
        all_previous_sessions=training_sessions[:1],
        street_circuit=0,
        weather_wet=0,
        track_temp=28.0,
    )
    race_dfs.append(df_chn)

    # Japan (Round 3): previous = Australia + China
    df_jpn = build_features_for_race(
        race_session=training_sessions[2],
        all_previous_sessions=training_sessions[:2],
        street_circuit=0,   # Suzuka = permanent circuit
        weather_wet=0,
        track_temp=24.0,
    )
    race_dfs.append(df_jpn)

    full_df = pd.concat(race_dfs, ignore_index=True)
    print(f"  ✓ Feature table: {len(full_df)} rows × {len(FEATURE_COLS)} features")
    print(f"  Podium distribution: {full_df['podium'].value_counts().to_dict()}")

    # ── STEP 3: LORO Cross-Validation ─────────────────────────────────────
    print("\n[3/5] Running Leave-One-Race-Out evaluation...")
    race_names = full_df["race"].unique().tolist()
    avg_scores = loro_evaluate(full_df, race_names)

    # ── STEP 4: Pick best model ────────────────────────────────────────────
    print("\n[4/5] Selecting best model...")
    best_model_name = pick_best_model(avg_scores)
    print(f"  ✓ Best model: {best_model_name}")

    # ── STEP 5: Build Miami features and predict ───────────────────────────
    print(f"\n[5/5] Building Miami features (QUALIFYING_DONE = {QUALIFYING_DONE})...")

    # CORRECT — consistent indentation
    MIAMI_WEATHER_WET, MIAMI_TRACK_TEMP = fetch_miami_weather()
    miami_df = build_miami_features(
        training_sessions,
        full_df,
        weather_wet=MIAMI_WEATHER_WET,
        track_temp=MIAMI_TRACK_TEMP
)
    print(f"  ✓ Miami feature table: {len(miami_df)} drivers")

    all_preds, importances = make_prediction(best_model_name, full_df, miami_df)

    # ── Print prediction to console ────────────────────────────────────────
    print("\n" + "=" * 65)
    status = "FINAL PREDICTION" if QUALIFYING_DONE else "PRE-QUALIFYING FORECAST"
    print(f"  🏁 MIAMI GP — {status}")
    print("=" * 65)
    print(f"  {'POS':<5} {'DRIVER':<8} {'TEAM':<28} {'PODIUM %'}")
    print("  " + "-" * 55)
    for p in all_preds[:10]:  # show top 10
        marker = " ⭐" if p["driver"] in ("HAM",) else ""
        print(f"  P{p['position']:<4} {p['driver']:<8} {p['team']:<28} {p['podium_prob']:>5.1f}%{marker}")

    print("\n  Top 3 feature importances:")
    top_feats = sorted(importances.items(), key=lambda x: -x[1])[:3]
    for feat, imp in top_feats:
        print(f"    {feat}: {imp:.4f}")

    # ── Save JSON ──────────────────────────────────────────────────────────
    save_prediction_json(all_preds, best_model_name, avg_scores, importances)

    print("\n  Done. Run again on May 3rd with QUALIFYING_DONE = True")
    print("  and real grid positions filled in MIAMI_GRID.")
    print("=" * 65)


if __name__ == "__main__":
    main()
