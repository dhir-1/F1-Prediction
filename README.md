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
 
A full-stack machine learning project that predicts Formula One podium finishes using real telemetry and race data pulled live from the F1 API via FastF1 — built race by race throughout the 2026 season.
 
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
│  Race Data        12 Features           XGBoost / RF        │
│  Lap Times        Grid Position         LORO Cross-Val       │
│  Pit Stops        Rolling Form          predict_proba()      │
│  Weather          Constructor Pace      ↓                   │
│                                    JSON Output              │
│                                         ↓                   │
│                                   FastAPI Route             │
│                                         ↓                   │
│                                  React Dashboard            │
└─────────────────────────────────────────────────────────────┘
```
 
### The 12 Features
 
| # | Feature | Why It Matters |
|---|---------|---------------|
| 1 | **Grid Position** | Most predictive single feature in F1 |
| 2 | Avg Finishing Position (last 3 races) | Current driver form |
| 3 | Constructor Avg Finish | Car pace indicator |
| 4 | Gap to Pole in Qualifying | Raw speed metric |
| 5 | Avg Pit Stop Time | Team execution under pressure |
| 6 | Avg Number of Pit Stops | Strategy tendency |
| 7 | Points Scored This Season | Form with DNF impact |
| 8 | Lap Time Consistency (std dev) | Racecraft indicator |
| 9 | DNFs This Season | Reliability signal |
| 10 | Street Circuit Flag | Circuit type characteristics |
| 11 | Weather: Dry/Wet | Wet races reshuffle everything |
| 12 | Track Temperature (°C) | Tyre degradation factor |
 
---
 
## 🔬 MODEL PERFORMANCE · MIAMI GP (Round 6)
 
```
╔══════════════════╦═══════╦═══════════╦════════╦═══════╗
║ Model            ║  F1   ║ Precision ║ Recall ║  AUC  ║
╠══════════════════╬═══════╬═══════════╬════════╬═══════╣
║ XGBClassifier ✓  ║ 0.857 ║   0.750   ║ 1.000  ║ 0.968 ║
║ Random Forest    ║ 0.419 ║   0.417   ║ 0.444  ║ 0.965 ║
║ XGBRegressor     ║ MAE   ║   3.053   ║  pos   ║  —    ║
╚══════════════════╩═══════╩═══════════╩════════╩═══════╝
 
Training · 3 races · 66 rows · Leave One Race Out CV
Winner   · XGBClassifier (F1 Score primary metric)
```
 
### Miami GP Pre-Qualifying Forecast
 
```
🏆  P1  RUS  Mercedes    85.2% confidence
🥈  P2  PIA  McLaren     84.5% confidence  
🥉  P3  ANT  Mercedes    83.9% confidence
 
Top feature importances:
  grid_position    ████████████████████  57.4%
  season_points    ████████              15.2%
  avg_pit_count    ███████               11.4%
```
 
---
 
## 🛠️ STACK
 
```
DATA LAYER          MODEL LAYER         API LAYER           UI LAYER
──────────          ───────────         ─────────           ────────
FastF1              XGBoost             FastAPI             React 19
Python 3.11         Random Forest       Uvicorn             Vite
requests            scikit-learn        CORS Middleware      TanStack Router
pandas              LORO Cross-Val      In-memory Cache     Tailwind CSS
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
│   │   │   └── site_data.py        ← /api/v1/site-data endpoint
│   │   └── core/
│   │       └── config.py           ← paths & config
│   ├── scripts/
│   │   ├── miami_prediction.py     ← Round 6
│   │   └── [race]_prediction.py   ← one per race
│   ├── data/
│   │   └── predictions/
│   │       └── miami-2026.json     ← model output
│   └── main.py                     ← FastAPI entry point
│
└── frontend/
    └── src/
        ├── routes/
        │   ├── index.tsx           ← Dashboard
        │   ├── predictions/        ← Prediction pages
        │   └── history.tsx         ← Season archive
        ├── components/
        └── lib/
            └── data.tsx            ← API context + helpers
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
Run prediction    Qualifying done    Race day 🏁       Update results
script with       ↓                  ↓                 ↓
estimated grid    Fill MIAMI_GRID    Watch & enjoy     Fill actualResult
↓                 Set QUALIFYING     ↓                 Add round to
Pre-Qualifying    _DONE = True       Update            completed_rounds
Forecast goes     Re-run script      standings         Hit /clear-cache
live              Final Prediction   ↓                 ↓
                  goes live          /clear-cache      Prediction vs
                                                       Reality page
                                                       updates
```
 
---
 
## ⚠️ KNOWN LIMITATIONS
 
- **Small dataset** — 66 rows (3 races × 22 drivers) is genuinely thin. Results should be interpreted with healthy scepticism.
- **Regulation change** — Miami runs under revised FIA energy management rules. Training data ran under different regulations. Mitigated via `new_regs` binary feature.
- **No historical track data** — No past Miami performance data used. Too few 2026 data points to include reliably.
- **Pre-qualifying grid** — Before qualifying, grid position is estimated from 2026 average. Final prediction (post-qualifying) is significantly more reliable.
- **New teams** — Cadillac data may be incomplete in FastF1 for early rounds.
---
 
## 📅 2026 SEASON TRACKER
 
| Round | Race | Status | Prediction |
|-------|------|--------|------------|
| R01 | 🇦🇺 Australian GP | ✅ Completed | — |
| R02 | 🇨🇳 Chinese GP | ✅ Completed | — |
| R03 | 🇯🇵 Japanese GP | ✅ Completed | — |
| R04 | 🇧🇭 Bahrain GP | ❌ Cancelled | — |
| R05 | 🇸🇦 Saudi Arabian GP | ❌ Cancelled | — |
| **R06** | **🇺🇸 Miami GP** | **🔴 Next** | **✅ Published** |
| R07 | 🇮🇹 Emilia Romagna GP | ⏳ Upcoming | — |
| R08 | 🇲🇨 Monaco GP | ⏳ Upcoming | — |
| … | … | … | … |
 
---
 
## 🏆 CHAMPIONSHIP STANDINGS (After R03)
 
```
DRIVERS                          CONSTRUCTORS
───────                          ────────────
1. ANT  Mercedes    68 pts       1. Mercedes     123 pts
2. RUS  Mercedes    55 pts       2. Ferrari       77 pts
3. LEC  Ferrari     42 pts       3. McLaren       38 pts
4. HAM  Ferrari     35 pts       4. Haas          17 pts
5. NOR  McLaren     20 pts       5. Alpine        16 pts
```
 
---
 
*Forza Ferrari · Built by Dhir · F1 2026*
 
```
████████████████████████████████████
█  LIGHTS OUT AND AWAY WE GO  🏁   █
████████████████████████████████████
```
 
