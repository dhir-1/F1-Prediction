from fastapi import APIRouter

from app.models.site import SiteDataResponse
from app.services.site_data_service import get_site_data

router = APIRouter(tags=["site"])


@router.get("/site-data", response_model=SiteDataResponse)
def read_site_data() -> SiteDataResponse:
    return get_site_data()

