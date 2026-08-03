from typing import Tuple

from fastapi import APIRouter, Form, BackgroundTasks
from app.services.normativa_sync import sync_normativa_legisalud, sync_normativa_PNGCAM, sync_normativa_from_single_url,generate_embeddings_for_all_documents
from app.ingestion.generate_embeddings_test import create_and_store_embeddings_test

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
    url: Tuple[str, str] = Form(...)
):
    result = sync_normativa_from_single_url(user_uid, url, background_tasks)

    return {
        "status": "sync_started",
        "details": result
    }

@router.post("/fix_PNGCAM_data")
async def fix_normativa_PNGCAM_endpoint(
    background_tasks: BackgroundTasks,
):
    #result = database.add_title_to_documents()
    result = generate_embeddings_for_all_documents()
    return {
        "status": "fix_started",
        "details": result
    }

@router.get("/create_test_embedding")
async def create_test_embedding(
    background_tasks: BackgroundTasks,
):
    #result = database.add_title_to_documents()
    result = create_and_store_embeddings_test(document_id="test")
    return {
        "status": "fix_started",
        "details": result
    }