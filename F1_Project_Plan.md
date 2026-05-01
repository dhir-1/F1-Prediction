# DHIR'S PIT WALL

## F1 2026 Race Prediction Project

*Full Project Plan & Reference Document*

**Starting Race:** Miami Grand Prix · May 4, 2026

## 1. Project Overview

This project predicts F1 race outcomes using machine learning. Each race gets its own prediction page on a React-based dashboard. Predictions are made manually by Dhir using real race data fetched via FastF1, model output, and personal analysis. The project is deployed on GitHub and updated race-by-race throughout the 2026 season.

### 1.1 Goals

- **Primary:** Predict the Miami GP podium (P1, P2, P3) using XGBoost and Random Forest trained on 2026 season data.
- **Secondary:** Build a public-facing dashboard (React + Vite + Tailwind) that displays predictions, reasoning, and post-race results.
- **Portfolio:** Demonstrate end-to-end ML project skills: data collection, feature engineering, model evaluation, deployment.
- **Ongoing:** After Miami, blend past race results to improve predictions for future races throughout the season.

### 1.2 Tech Stack

- **Data:** FastF1 (Python library for F1 telemetry and results)
- **Modelling:** XGBoost, Random Forest, scikit-learn — run in Google Colab
- **Tuning:** GridSearchCV or RandomizedSearchCV
- **Frontend:** React + Vite + Tailwind CSS
- **Deployment:** GitHub Pages or Vercel (free tier)
- **Version control:** GitHub — commit regularly after every major step

## 2. Data Strategy

### 2.1 Data Source

Use FastF1 Python library to pull 2026 season race data. Only 2026 data is used — no historical seasons. Currently 3 races available:

- Round 1: Australia (Melbourne)
- Round 2: China (Shanghai)
- Round 3: Japan (Suzuka)

> **Note:** Bahrain and Saudi Arabia were cancelled due to conflict in the Middle East.
>
> This leaves 3 races × 22 drivers = 66 rows of training data.
>
> This is a small dataset. Model simplicity and honest evaluation are important.

### 2.2 Target Variable

Predict finishing position as a number (1 through 22). This is treated as:

- **XGBRegressor approach:** Predict finish position directly. Sort all drivers by predicted value. Lowest = predicted winner.
- **XGBClassifier approach:** Predict podium class (P1 / P2 / P3 / rest). Use `predict_proba()` to get confidence %.

*Both approaches will be tried and compared. The better performing model is used for the final prediction page.*

### 2.3 Train / Test Split Strategy

With only 66 rows, standard train/test split wastes too much data. Use Leave One Race Out (LORO) cross-validation:

- Round 1: Train on China + Japan → Test on Australia
- Round 2: Train on Australia + Japan → Test on China
- Round 3: Train on Australia + China → Test on Japan

*This approach respects the time ordering of races and mirrors real-world prediction: you always train on past races to predict a future one.*

### 2.4 Class Imbalance Handling

If using classifier: podium = 1 is a minority class. Handle with:

- **scale_pos_weight (XGBoost):** Set to non-podium count / podium count (approx 5–6x).
- **class_weight='balanced' (Random Forest):** Sklearn handles it automatically.
- **StratifiedKFold:** Ensures each fold has proportional class representation.

## 3. Feature Engineering

### 3.1 Final Feature List (12 Features)

All features must be knowable **before** the race starts. No post-race data allowed.

| # | Feature | Source | Notes |
|---|---|---|---|
| 1 | Grid Position | Manual entry | Added the day before race after qualifying (May 3rd for Miami). Most important feature. |
| 2 | Avg Finishing Position (last 3 races) | FastF1 | Current driver form. Rolling average over all 2026 races. |
| 3 | Constructor Avg Finish (2026) | FastF1 | Reflects car pace. Sometimes more predictive than driver alone. |
| 4 | Gap to Pole in Qualifying (seconds) | FastF1 | Raw car speed indicator. Gap = driver quali time minus pole time. |
| 5 | Avg Pit Stop Time | FastF1 | Team execution speed. Faster stops = competitive advantage. |
| 6 | Avg Number of Pit Stops | FastF1 | Strategy tendency per team/driver. |
| 7 | Points Scored This Season | FastF1 | Another form metric. Correlated with avg finish but captures DNF impact. |
| 8 | Lap Time Consistency (std dev) | FastF1 | Lower std dev = more consistent driver. Good racecraft indicator. |
| 9 | DNFs This Season | FastF1 | Reliability indicator. More DNFs = less predictable finishes. |
| 10 | Street Circuit (1/0) | Manual | Miami is semi-permanent. Flag for circuit type characteristics. |
| 11 | Weather: Dry/Wet (1/0) | Manual / FastF1 | Binary flag. Wet conditions reshuffle the grid significantly. |
| 12 | Track Temperature (°C) | FastF1 | Affects tyre degradation and strategy. Miami tends to be hot. |

> **Regulation Change Note (Important for Miami):**
>
> The FIA introduced energy management rule changes effective from Miami GP, after driver complaints and Bearman's crash at Suzuka. This means your 3 training races ran under different regulations than Miami will. Add a binary feature `new_regs = 1` for Miami (`0` for training races) to flag this.
>
> Also note this as a limitation in your model transparency section on the prediction page.

### 3.2 Grid Position Handling

Grid position is unavailable until qualifying (May 3rd, day before Miami). Handle in two stages:

- **Stage 1 – Pre-qualifying prediction:** Use average qualifying position from 2026 season as a proxy. Run model and display as `Pre-Qualifying Forecast` with lower confidence.
- **Stage 2 – Post-qualifying update:** Manually insert real grid positions on May 3rd evening. Re-run model. Display as `Final Prediction` on website.

## 4. Modelling Pipeline

### 4.1 Models to Train

- **XGBClassifier:** Predicts class (podium/position). Use `predict_proba()` for confidence scores. Good for showing % on prediction page.
- **XGBRegressor:** Predicts finish position as a number. Sort output to get predicted order. Often better with small datasets.
- **Random Forest Classifier/Regressor:** Baseline model. Simple, interpretable, handles small data well.

*Train all three. Compare. Best performer wins and gets used for the public prediction.*

### 4.2 Hyperparameter Tuning

- **Method:** GridSearchCV or RandomizedSearchCV (Optuna is overkill for 66 rows — risk of overfitting to tiny sample).
- **CV Strategy:** StratifiedKFold with 5 folds inside each LORO round.
- **XGBoost key params to tune:** `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `scale_pos_weight`.
- **Random Forest key params:** `n_estimators`, `max_depth`, `min_samples_split`, `class_weight`.

### 4.3 Evaluation Metrics

Accuracy alone is misleading on imbalanced data. Use all of these:

- **F1 Score:** Harmonic mean of precision and recall. Primary metric.
- **Precision:** Of predicted podiums, how many were real? Avoid false alarms.
- **Recall:** Of actual podiums, how many did we catch? Don't miss real finishers.
- **ROC-AUC:** Overall model discrimination ability across all thresholds.
- **MAE (for regressor only):** Mean Absolute Error on predicted finishing position.

*For race prediction, recall matters slightly more than precision. Missing a real podium finisher is a worse error than occasionally over-predicting.*

## 5. Prediction Page Design

### 5.1 Page Structure

Each race gets one dedicated prediction page. The Miami page will have three main sections:

#### Section A: Podium Prediction

- P1, P2, P3 driver cards with team colour, driver name, team name
- Confidence % from `predict_proba()` for each position
- Status badge: `Pre-Qualifying Forecast` / `Final Prediction` / `Result In`

#### Section B: Race Breakdown & Reasoning

- Key factors table: grid position, recent form, track characteristics, weather
- Written analysis (manually authored by Dhir) explaining the pick
- Regulation change note for Miami specifically
- Post-race: actual result vs prediction comparison

#### Section C: Model Transparency

- Which model was used (XGBClassifier or XGBRegressor)
- Features used and why
- Training data: Australia + China + Japan (66 rows)
- Evaluation scores: F1, Precision, Recall, ROC-AUC
- Known limitations: small dataset, regulation change, no historical track data

### 5.2 Race Archive

All past race predictions stay accessible. Navigation will show a list of all races with status indicators. Clicking a race opens its prediction page. Miami is the first entry. Future races are added one by one as the season progresses.

### 5.3 Blending Future Predictions

From Imola onwards, past race results feed into future predictions. The blending is done manually in the written reasoning section, not automated. Example logic:

- Hamilton strong in heat at Miami (street circuit, high temp) → adjust confidence up for Baku
- Norris poor tyre management in China → adjust confidence down for high-deg circuits

*This can evolve into a weighted feature later in the season if enough data accumulates.*

## 6. Website Architecture (React + Vite + Tailwind)

### 6.1 Pages

- **/** (Home / Dashboard): Existing HTML dashboard converted to React. Standings, countdown, ticker, Miami preview.
- **/predictions:** Race archive list. All races with status badges.
- **/predictions/miami-2026:** Miami specific prediction page (3 sections described above).
- **/predictions/[race-slug]:** Template reused for every future race.

### 6.2 Data Structure

Each race prediction is stored as a JavaScript/JSON object with this shape:

```json
{
  "raceName": "",
  "round": "",
  "circuit": "",
  "date": "",
  "status": "",
  "predictedPodium": [{"pos": "", "driver": "", "team": "", "confidence": ""}],
  "reasoning": "",
  "modelUsed": "",
  "features": [],
  "metrics": {},
  "actualResult": []
}
```

You edit this object manually for each race. The UI reads from it and renders accordingly. No database needed.

### 6.3 Dashboard Improvements (from existing HTML)

- Make standings interactive (sortable, filterable)
- Add navigation between Dashboard and Predictions
- Keep Miami neon colour theme and animations
- Countdown timer component (already working in HTML, port to React)
- Ticker component (already working, port to React)

## 7. Build & Deployment Plan

### 7.1 Phase-by-Phase Roadmap

| Phase | Timing | What to Do |
|---|---|---|
| Phase 1 | Now (Apr 22) | Finalise this plan. Set up GitHub repo. Create React + Vite + Tailwind project scaffold. |
| Phase 2 | Apr 23–25 | Migrate existing HTML dashboard to React components. Connect GitHub. First commit. |
| Phase 3 | Apr 25–28 | FastF1 data collection in Google Colab. Pull Australia, China, Japan. Build feature dataset. |
| Phase 4 | Apr 28–30 | Train models. XGBClassifier vs XGBRegressor vs Random Forest. Evaluate. Pick best. |
| Phase 5 | Apr 30 – May 2 | Build prediction page in React. Add pre-qualifying Miami prediction. Deploy to GitHub Pages. |
| Phase 6 | May 3 (evening) | Qualifying done. Add real grid positions manually. Re-run model. Update prediction page. |
| Phase 7 | May 4 | Race day. Watch and enjoy. After race, update page with actual result vs prediction. |
| Phase 8 | Post-Miami | Review model performance. Start blending for next race. Repeat cycle. |

### 7.2 GitHub Workflow

- **Repo name suggestion:** `f1-pit-wall` or `dhir-pit-wall`
- **Branching:** Work on `main` for now. Later use feature branches per race.
- **Commit frequency:** After every meaningful step. Don't batch everything into one giant commit.
- **Deployment:** Vercel is easiest for Vite projects. Connect repo, it auto-deploys on every push to `main`.
- **.gitignore:** Exclude `node_modules`, `.env`, `__pycache__`, `.ipynb_checkpoints`

## 8. Known Limitations & Honest Notes

Document these in your model transparency section on the website. Being upfront about limitations is a sign of good ML practice and makes the project more credible.

- **Small dataset:** 66 rows (3 races × 22 drivers) is genuinely thin for ML. Model may overfit. Results should be interpreted with caution.
- **Regulation change:** Miami runs under revised energy management rules. Training data (3 races) was under different regulations. Added `new_regs` binary feature to partially account for this.
- **No historical track data:** No past Miami-specific performance data used. Track history feature excluded to keep data clean.
- **Grid position unavailable pre-qualifying:** Pre-qualifying prediction uses estimated grid. Final prediction is more reliable.
- **22 drivers but some data may be incomplete:** New teams like Cadillac may have missing data in FastF1 for early rounds. Handle with imputation or exclusion.
- **DNFs in only 3 races:** DNF feature may not be very informative yet. Monitor after more races.

## 9. Quick Reference Cheatsheet

### Key Numbers

- **Training rows:** 66 (3 races × 22 drivers)
- **Features:** 12
- **CV Strategy:** Leave One Race Out (LORO)
- **Miami race date:** May 4, 2026 at 16:00 ET
- **Qualifying date:** May 3, 2026 (add grid positions this evening)
- **Target variable:** Finishing position (1–22)

### Feature Quick List

- Grid Position (manual — day before)
- Avg Finishing Position last 3 races
- Constructor Avg Finish 2026
- Gap to Pole in Qualifying
- Avg Pit Stop Time
- Avg Number of Pit Stops
- Points Scored This Season
- Lap Time Consistency (std dev)
- DNFs This Season
- Street Circuit (1/0)
- Weather Dry/Wet (1/0)
- Track Temperature (°C)

### Models to Compare

- XGBClassifier with `predict_proba()`
- XGBRegressor (sort output for predicted order)
- Random Forest (baseline)

### Evaluation Metrics

- F1 Score (primary)
- Precision
- Recall
- ROC-AUC
- MAE (regressor only)

*Forza Ferrari · Dhir's Pit Wall · F1 2026*
