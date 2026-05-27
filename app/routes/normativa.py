from fastapi import APIRouter, Form, BackgroundTasks
from app.services.normativa_sync import sync_normativa_legisalud, sync_normativa_PNGCAM, sync_normativa_from_single_url

router = APIRouter()

@router.post("/update_legisalud_data")
async def sync_normativa_legisalud_endpoint(
    background_tasks: BackgroundTasks,
    user_uid: str = Form(...)
):
    result = sync_normativa_legisalud(user_uid, background_tasks)

    return {
        "status": "sync_started",
        "details": result
    }


@router.post("/update_PNGCAM_data")
async def sync_normativa_PNGCAM_endpoint(
    background_tasks: BackgroundTasks,
    user_uid: str = Form(...)
):
    result = sync_normativa_PNGCAM(user_uid, background_tasks)

    return {
        "status": "sync_started",
        "details": result
    }


@router.post("/update_normativa_from_single_url")
async def sync_normativa_from_single_url_endpoint(
    background_tasks: BackgroundTasks,
    user_uid: str = Form(...),
    url: str = Form(...)
):
    result = sync_normativa_from_single_url(user_uid, url, background_tasks)

    return {
        "status": "sync_started",
        "details": result
    }