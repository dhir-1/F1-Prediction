# Dhir's Pit Wall

Full-stack F1 prediction project for the 2026 season.

## Structure

- `frontend/`
  React + Vite + Tailwind frontend using the exact `dhir-s-race-hub-main` design language.
- `backend/`
  Python prediction pipeline plus a FastAPI layer that serves site data to the frontend.
- `reference/`
  Preserved design reference source.
- `F1_Project_Plan.md`
  Project plan and product direction.

## Frontend

- Entry app: `frontend/src`
- Shared site-data provider: `frontend/src/lib/data.ts`
- Dev server proxy: `frontend/vite.config.ts`

## Backend

- API app: `backend/app/main.py`
- Site-data service: `backend/app/services/site_data_service.py`
- Prediction pipeline: `backend/app/ml/pipeline.py`
- Regeneration script: `backend/scripts/generate_prediction.py`
- Miami prediction JSON: `backend/data/predictions/miami-2026.json`

## Suggested local workflow

1. Create a Python environment inside `backend/` and install `backend/requirements.txt`.
2. Run the API with `uvicorn app.main:app --reload` from the `backend/` folder.
3. Install frontend dependencies inside `frontend/`.
4. Run the frontend with `npm run dev` from the `frontend/` folder.
5. Before Miami qualifying updates, rerun `backend/scripts/generate_prediction.py` after changing the grid inputs.
