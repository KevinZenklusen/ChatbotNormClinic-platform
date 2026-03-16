from fastapi import APIRouter, Form, BackgroundTasks
from app.services.normativa_sync import sync_normativa

router = APIRouter()

@router.post("/update_legisalud_data")
async def sync_normativa_endpoint(
    background_tasks: BackgroundTasks,
    user_uid: str = Form(...)
):
    result = sync_normativa(user_uid, background_tasks)

    return {
        "status": "sync_started",
        "details": result
    }
