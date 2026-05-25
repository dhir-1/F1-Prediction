# 🏎️ DHIR'S PIT WALL
## F1 2026 · Machine Learning Race Prediction Dashboard

```
████████████████████████████████████████████████████████████████
█                                                              █
█   P1  DHIR'S PIT WALL    2026 SEASON    RACE PREDICTIONS    █
█                                                              █
████████████████████████████████████████████████████████████████
```

> *"In Formula One, data is everything. This is my attempt to let the numbers speak."*

A full-stack machine learning project that predicts Formula One podium finishes using real telemetry and race data pulled live from the F1 API via FastF1 — built race by race throughout the 2026 season. Each round gets its own prediction script, tuned to the circuit, format, and data available at the time.

---

## ⚡ LIVE PREVIEW

> Frontend · React + Vite · TanStack Router
> Backend · FastAPI · Python 3.11
> Data · FastF1 · Live 2026 Season

---

## 🏁 HOW IT WORKS

```
┌─────────────────────────────────────────────────────────────┐
│                    PREDICTION PIPELINE                       │
│                                                             │
│  FastF1 API  →  Feature Engineering  →  Model Training      │
│      ↓                  ↓                     ↓             │
│  Race Data        Per-Race Features     Model (varies)      │
│  Lap Times        Rolling Form          LORO / GridSearch   │
│  Pit Stops        Constructor Pace      predict_proba()     │
│  Sprint Results   Reliability Score     ↓                   │
│  Weather                           JSON Output              │
│                                         ↓                   │
│                                   FastAPI Route             │
│                                         ↓                   │
│                                  React Dashboard            │
└─────────────────────────────────────────────────────────────┘
```

### Feature Pool

Features used vary per round depending on data availability and circuit characteristics. The pool includes:

| Feature | Why It Matters |
|---------|---------------|
| **Grid / Sprint Position** | Saturday pace signal — used where qualifying or sprint data is available |
| Avg Finishing Position (last 3 races) | Current driver form |
| Finish Trend | Slope of recent results — improving or declining |
| Constructor Avg Finish | Car pace indicator |
| Points Per Race (season) | Weighted form including DNF impact |
| Avg Lap Time Delta (vs winner) | Raw pace metric |
| Tyre Consistency (std dev within stints) | Racecraft and smooth driving indicator |
| Avg Grid Position (season) | Qualifying baseline when single-race grid not used |
| DNF Count | Raw reliability signal |
| Reliability Score | Points scored vs maximum possible — weights DNF cost by expected finish |
| Street Circuit Flag | Circuit type characteristics |
| Weather: Dry/Wet | Wet races reshuffle the order |
| Track Temperature (°C) | Tyre degradation factor |

> **Not every feature is used every round.** Each script documents exactly which features were active and why others were dropped.

---

## 🤖 MODEL STRATEGY

The model choice evolves round by round as the training dataset grows and circuit-specific factors change. Each prediction script documents what was used and why.

| Approach | When Used |
|----------|-----------|
| **XGBClassifier** (single, LORO CV) | Early season — simple, interpretable, fast |
| **VotingClassifier** (XGB + XGBReg + RF, GridSearch) | Sprint weekends — more signal available, ensemble reduces variance |
| More to come | As data grows, more sophisticated approaches become viable |

**Cross-validation** also adapts per round:
- **LORO (Leave One Race Out)** — used when interpretability and small-data robustness matter
- **GridSearch k-Fold** — used for hyperparameter tuning when ensemble voting is used

---

## 🛠️ STACK

```
DATA LAYER          MODEL LAYER         API LAYER           UI LAYER
──────────          ───────────         ─────────           ────────
FastF1              XGBoost             FastAPI             React 19
Python 3.11         Random Forest       Uvicorn             Vite
requests            scikit-learn        CORS Middleware      TanStack Router
pandas              VotingClassifier    In-memory Cache     Tailwind CSS
numpy               predict_proba()     JSON endpoints      shadcn/ui
```

---

## 📁 PROJECT STRUCTURE

```
dhirs-pit-wall/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── site_data.py          ← /api/v1/site-data endpoint
│   │   └── core/
│   │       └── config.py             ← paths & config
│   ├── scripts/
│   │   ├── miami_prediction.py       ← Round 4 · XGBClassifier · LORO
│   │   ├── canada_prediction.py      ← Round 5 · VotingClassifier · GridSearch
│   │   └── [race]_prediction.py      ← one per race going forward
│   ├── data/
│   │   └── predictions/
│   │       ├── miami-2026.json
│   │       ├── canada-2026.json
│   │       └── [race]-2026.json
│   └── main.py                       ← FastAPI entry point
│
└── frontend/
    └── src/
        ├── routes/
        │   ├── index.tsx             ← Dashboard
        │   ├── predictions/          ← Per-race prediction pages
        │   └── history.tsx           ← Season archive
        ├── components/
        └── lib/
            └── data.tsx              ← API context + helpers
```

---

## 🚀 RUNNING LOCALLY

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 🔄 RACE PREDICTION WORKFLOW

```
THURSDAY          SATURDAY           SUNDAY            POST-RACE
────────          ────────           ──────            ─────────
Run prediction    Sprint / Quali     Race day 🏁       Update results
script with       done               ↓                 ↓
estimated grid    ↓                  Watch & enjoy     Fill actualResult
↓                 Re-run script                        Add round to
Pre-race          with real          ↓                 completed_rounds
forecast          Saturday data      /clear-cache      Hit /clear-cache
goes live         ↓                                    ↓
                  Final prediction                     Prediction vs
                  goes live                            Reality updates
```

---

## 📅 2026 SEASON TRACKER

| Round | Race | Status | Model Used | Prediction | Actual P1 |
|-------|------|--------|------------|------------|-----------|
| R01 | 🇦🇺 Australian GP | ✅ Completed | — | — | RUS |
| R02 | 🇨🇳 Chinese GP | ✅ Completed | — | — | ANT |
| R03 | 🇯🇵 Japanese GP | ✅ Completed | — | — | ANT |
| R04 | 🇧🇭 Bahrain GP | ❌ Cancelled | — | — | — |
| R05 | 🇸🇦 Saudi Arabian GP | ❌ Cancelled | — | — | — |
| **R04** | **🇺🇸 Miami GP** | **✅ Completed** | XGBClassifier · LORO | ✅ Published | ANT |
| **R05** | **🇨🇦 Canadian GP** | **✅ Completed** | VotingClassifier · GridSearch | ✅ Published | ANT |
| **R06** | **🇲🇨 Monaco GP** | **🔴 Next** | TBD | ⏳ Pending | — |
| R07 | 🇪🇸 Barcelona-Catalunya GP | ⏳ Upcoming | — | — | — |
| R08 | 🇦🇹 Austrian GP | ⏳ Upcoming | — | — | — |
| … | … | … | … | … | … |

> **Note:** Bahrain and Saudi were cancelled due to regional disruption. The Emilia Romagna GP at Imola is not on the 2026 calendar. Round numbers reflect the revised 22-race schedule.

---

## 🏆 CHAMPIONSHIP STANDINGS (After R05 · Canada)

```
DRIVERS                          CONSTRUCTORS
───────                          ────────────
1. ANT  Mercedes   131 pts       1. Mercedes    219 pts
2. RUS  Mercedes    88 pts       2. Ferrari     147 pts
3. LEC  Ferrari     75 pts       3. McLaren     106 pts
4. HAM  Ferrari     72 pts       4. Red Bull     57 pts
5. NOR  McLaren     58 pts       5. Alpine       35 pts
6. PIA  McLaren     48 pts       6. Racing Bulls 21 pts
7. VER  Red Bull    43 pts       7. Haas         19 pts
8. GAS  Alpine      20 pts       8. Williams      7 pts
9. BEA  Haas        18 pts       9. Audi          2 pts
10. LAW Racing Bulls 16 pts
```

---

## ⚠️ KNOWN LIMITATIONS

- **Small dataset** — grows by ~22 rows per race. Early predictions are made on thin data and should be interpreted with healthy scepticism.
- **Regulation change** — 2026 runs under revised FIA energy management rules. Training data from the same season mitigates this but the first few rounds carry uncertainty.
- **Model drift** — the model choice and feature set evolve each round. Historical prediction JSONs preserve the exact approach used at the time.
- **Sprint weekends** — sprint result is used as a feature post-Saturday. Pre-sprint forecasts fall back to grid/season-average proxies.
- **Upgrade impact** — car upgrade packages (e.g. McLaren's Canada front wing, Cadillac's curb kit) are not capturable from historical lap data.
- **New teams** — Cadillac data may be incomplete in FastF1 for early rounds.
- **Street circuits** — Monaco and other street circuits have very limited historical lap time data making pace comparisons harder.

---

## 📋 PER-ROUND MODEL NOTES

### R04 · Miami GP
- **Model:** XGBClassifier (single)
- **CV:** Leave One Race Out (LORO)
- **Features:** 12 including grid position, weather, street circuit flag
- **Key finding:** `grid_position` dominated at 57.4% importance — excluded in subsequent rounds

### R05 · Canadian GP
- **Model:** VotingClassifier — XGBClassifier + XGBRegressorClassifier + RandomForest (soft voting)
- **CV:** GridSearch 3-fold for tuning; full train for final model
- **Features:** 9 base features + `sprint_position` (post-Saturday)
- **Key change:** Grid position removed by design; sprint result used as Saturday pace signal instead
- **Training data:** Australia, China, Japan, Miami (88 rows)

### R06 · Monaco GP
- ⏳ Script in progress — approach TBD based on street circuit characteristics

---

*Forza Ferrari · Built by Dhir · F1 2026*

```
████████████████████████████████████
█  LIGHTS OUT AND AWAY WE GO  🏁   █
████████████████████████████████████
```
