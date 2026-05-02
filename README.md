# DHIR'S PIT WALL
### F1 2026 · Race Prediction Dashboard

A full-stack machine learning project that predicts Formula One race outcomes using real telemetry data from FastF1, trained on 2026 season results.

---

## STACK

| Layer | Tech |
|---|---|
| Data | FastF1 |
| Models | XGBoost · Random Forest · scikit-learn |
| Backend | FastAPI · Python 3.11 |
| Frontend | React · Vite · TanStack Router · Tailwind CSS |
| Deployment | Vercel |

---

## HOW IT WORKS

1. **Data** — FastF1 pulls live 2026 race results, lap times, pit stop data, and qualifying gaps directly from the F1 API
2. **Features** — 12 pre-race features engineered per driver: grid position, rolling form, constructor pace, pit stop efficiency, lap consistency, and more
3. **Models** — XGBClassifier, XGBRegressor, and Random Forest trained using Leave One Race Out (LORO) cross-validation
4. **Prediction** — Best model selected by F1 score, confidence % generated via `predict_proba()`
5. **Frontend** — React dashboard displays standings, race calendar, and prediction pages per race

---

## PROJECT STRUCTURE
f1-pit-wall/
├── backend/
│   ├── app/
│   │   ├── api/          ← FastAPI routes
│   │   └── core/         ← Config
│   ├── scripts/          ← Prediction scripts (one per race)
│   ├── data/
│   │   └── predictions/  ← Generated JSON per race
│   └── main.py
└── frontend/
└── src/
├── routes/       ← Dashboard, predictions, history
├── components/
└── lib/          ← Data context + helpers

---

## RUNNING LOCALLY

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## RACE PREDICTION WORKFLOW

Before race weekend   → Run scripts/[race]_prediction.py
After qualifying      → Set QUALIFYING_DONE = True, fill grid positions, re-run
After race            → Update completed_rounds in site_data.py, fill actualResult

---

## MODEL PERFORMANCE · MIAMI GP

| Model | F1 | Precision | Recall | AUC |
|---|---|---|---|---|
| XGBClassifier ✓ | 0.857 | 0.750 | 1.000 | 0.968 |
| Random Forest | 0.419 | 0.417 | 0.444 | 0.965 |

Training data: 3 races · 66 rows · Leave One Race Out CV

---

## KNOWN LIMITATIONS

- Small dataset (66 rows) — model may overfit
- Miami runs under revised energy management regulations
- Grid position estimated pre-qualifying
- No historical Miami-specific track data used

---

*Forza Ferrari · Built by Dhir · 2026*