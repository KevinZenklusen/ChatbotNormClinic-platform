from datetime import datetime, timezone
import hashlib
import uuid
from fastapi import BackgroundTasks
from typing import Tuple
import requests
from requests.exceptions import RequestException
from app.services.web_crawler import discover_links, get_urls_normativa_PNGCAM
from app.core.config import LEGISALUD_URL, PNGCAM_URL, ALLOWED_DOMAINS
from app.core.database_client import database
from app.core.storage_client import save_file_in_blob_storage
from app.ingestion.generate_embeddings import create_and_store_embeddings


def sync_normativa_legisalud(user_uid: str, background_tasks: BackgroundTasks):
    """
    Sync específico para legisalud,
    aplicando reglas especiales de filtrado y normalización.
    """
    urls = discover_links(LEGISALUD_URL, ALLOWED_DOMAINS)

    for url in urls:
        try:
            process_single_url(url, user_uid, background_tasks)
        except Exception as e:
            print(f"[CRITICAL] Error de proceamiento inesperado {url}: {e}")


def process_single_url(url_data: Tuple[str, str], user_uid: str, background_tasks):

    title = url_data[0]
    url = url_data[1]

    print(f"Descargando datos desde {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

    except RequestException as e:
        print(f"[ERROR] Error al obtener {url} → {str(e)}")
        return {"status": "error", "url": url}

    contents = response.content
    content_hash = hashlib.sha256(contents).hexdigest()

    existing = database.get_document_by_source_url(user_uid, url)

    filename = url.split("/")[-1] or "index.html"
    
    if not existing:

        # CASO: Documento nuevo

        blob_url = save_file_in_blob_storage(
            file_bytes=contents,
            filename=filename,
            user_uid=user_uid
        )

        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc)

        database.insert_document_data(
            document_id=document_id,
            user_uid=user_uid,
            content_hash=content_hash,
            blob_url=blob_url,
            source_url=url,
            created_at=created_at,
            status = "UPLOADED",
            title=title
        )

        background_tasks.add_task(
            create_and_store_embeddings,
            document_id=document_id
        )
        print("Descarga de URL finalizada")
        return {"status": "new", "document_id": document_id}
    
    # CASO: Existe y NO cambió

    if existing["content_hash"] == content_hash:
        return {"status": "unchanged", "document_id": existing["document_id"]}

    # CASO: Existe pero CAMBIÓ → reemplazar

    document_id = existing["document_id"]

    # BORRAR embeddings viejos
    database.delete_embeddings(document_id)

    # Guardar nueva versión en blob
    blob_url = save_file_in_blob_storage(
        file_bytes=contents,
        filename=filename,
        user_uid=user_uid
    )

    # Actualizar metadata
    database.update_document_content(
        document_id=document_id,
        content_hash=content_hash,
        blob_url=blob_url
    )

    database.update_document_status(document_id, "UPLOADED")

    # Reindexar
    background_tasks.add_task(
        create_and_store_embeddings,
        document_id=document_id
    )

    return {"status": "updated", "document_id": document_id}


def update_existing_document(existing, contents, new_hash, background_tasks):

    document_id = existing["document_id"]

    # Borrar embeddings anteriores
    database.delete_embeddings(document_id)

    # Reemplazar blob
    blob_url = save_file_in_blob_storage(
        file_bytes=contents,
        filename=existing["source_url"].split("/")[-1],
        user_uid=existing["user_uid"]
    )

    # Actualizar metadata
    database.update_document_content(
        document_id=document_id,
        content_hash=new_hash,
        blob_url=blob_url
    )

    database.update_document_status(document_id, "UPLOADED")

    # Reindexar
    background_tasks.add_task(
        create_and_store_embeddings,
        document_id=document_id
    )


def sync_normativa_PNGCAM(user_uid: str, background_tasks: BackgroundTasks):
    """
    Sync específico para PNGCAM,
    aplicando reglas especiales de filtrado y normalización.
    """

    visited = set()

    urls = get_urls_normativa_PNGCAM(
        base_url=PNGCAM_URL,
        allowed_domains=ALLOWED_DOMAINS,
        visited=visited
    )

    print(f"[sync_normativa_argentina_gob] Procesando {len(urls)} URLs")

    for url in urls:
        try:
            process_single_url(url, user_uid, background_tasks)
        except Exception as e:
            print(f"[CRITICAL] Error de procesamiento inesperado {url}: {e}")


def sync_normativa_from_single_url(user_uid: str, url: Tuple[str, str], background_tasks: BackgroundTasks):

    try:
        process_single_url(url, user_uid, background_tasks)
    except Exception as e:
        print(f"[CRITICAL] Error de proceamiento inesperado {url}: {e}")


def generate_embeddings_for_all_documents():
    """
    Esta función sirve para generar embeddings en todos los documentos cargados
    en los que haya fallado la generación de embeddings (ERROR)
    """ 

    document_ids = []

    with database._conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM documents where status ILIKE '%ERROR%';")
        document_ids = [row[0] for row in cur.fetchall()]

    total = len(document_ids)
    print(f"Total documentos: {total}")

    for i, doc_id in enumerate(document_ids, start=1):
        try:
            create_and_store_embeddings(document_id=str(doc_id))

            if i % 50 == 0:
                print(f"Procesados {i}/{total}")

        except Exception as e:
            print(f"[ERROR] document_id {doc_id}: {e}")
