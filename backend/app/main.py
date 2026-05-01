from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.site import router as site_router
from app.core.config import FRONTEND_DEV_ORIGINS

app = FastAPI(
    title="Dhir's Pit Wall API",
    version="1.0.0",
    description="Backend API for the Dhir's Pit Wall dashboard and prediction pages.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(site_router, prefix="/api/v1")

