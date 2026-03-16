from fastapi import APIRouter, File, Form, UploadFile, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timezone
from psycopg2.errors import UniqueViolation
import hashlib
import uuid

from app.ingestion.generate_embeddings import create_and_store_embeddings
from app.core.storage_client import save_file_in_blob_storage
from app.core.database_client import database

router = APIRouter()

@router.post("/upload")
async def subir_archivo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_uid: str = Form(...)
):
    contents = await file.read()
    await file.close()

    content_hash = hashlib.sha256(contents).hexdigest()

    existing = database.document_exists(
        user_uid=user_uid,
        content_hash=content_hash
    )

    if existing:
        print("Exists")
        return {
            "status": "already_exists",
            "document_id": existing["document_id"],
            "hash": content_hash
        }

    blob_url = await run_in_threadpool(
        save_file_in_blob_storage,
        file_bytes=contents,
        filename=file.filename,
        user_uid=user_uid
    )

    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc)

    try:
        database.insert_document_data(
            document_id=document_id,
            user_uid=user_uid,
            content_hash=content_hash,
            blob_url=blob_url,
            source_url=blob_url,
            created_at=created_at,
            status="UPLOADED"
        )
    except UniqueViolation:
        existing = database.document_exists(
            user_uid=user_uid,
            content_hash=content_hash
        )
        return {
            "status": "already_exists",
            "document_id": existing["document_id"],
            "hash": content_hash
        }

    background_tasks.add_task(
        create_and_store_embeddings,
        document_id=document_id
    )

    return {"status": "processing", "document_id": document_id}
