from datetime import datetime, timezone
import hashlib

from app.ingestion.processors.registry import get_processor
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document as langchain_Document

from app.ingestion.resource_loader import load_resource
from app.core.embedding import obtener_modelo_de_embeddings
from app.core.database_client import database

COLLECTION_NAME = "documents"


def create_and_store_embeddings(
    *,
    document_id: str
):
    try:
        database.update_document_status(document_id, "INDEXING")
        document_data = database.get_document_data(document_id)
        embedding_model = obtener_modelo_de_embeddings()
        resource = load_resource(document_data["source_url"])
        processor = get_processor(resource["content_type"])

        document_url = document_data["source_url"]
        print(f"Generando embeddings para {document_url}")

        pages = processor.extract_pages(resource["bytes"])

        if not pages:
            return {"status": "empty"}

        docs = []

        for page_number, page_text in enumerate(pages, start=1):
            if not page_text or not page_text.strip():
                continue

            docs.append(
                langchain_Document(
                    page_content=page_text,
                    metadata={
                        "blob_name": document_data["blob_url"],
                        "document_id": document_id,
                        "content_hash": document_data["content_hash"],
                        "extension": processor.extension(),
                        "user_uid": document_data["user_uid"],
                        "type": processor.document_type(),
                        "creation_datetime": document_data["created_at"].isoformat(),
                        "page_number": page_number,
                        "source_url": document_data["source_url"]
                    }
                )
            )

        if not docs:
            return {"status": "empty"}

        splitter = SemanticChunker(
            embedding_model,
            breakpoint_threshold_type="percentile"
        )

        chunks = splitter.split_documents(docs)

        if not chunks:
            return {"status": "empty"}

        ids = [
            f"{document_id}_{i}"
            for i in range(len(chunks))
        ]

        database.create_and_store_embeddings(
            collection_name=COLLECTION_NAME,
            documents=chunks,
            embedding_function=embedding_model,
            ids=ids
        )

        database.update_document_status(document_id, "READY")

        return {
            "status": "ok",
            "document_id": document_id,
            "hash": document_data["content_hash"]
        }

    except Exception as e:
        database.update_document_status(document_id, "ERROR")
        raise