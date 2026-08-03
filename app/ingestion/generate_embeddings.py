from langchain_core.documents import Document as langchain_Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.processors.registry import get_processor
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

        title = document_data.get("title", "")

        full_text = ""
        page_boundaries = []

        for page_number, page_text in enumerate(pages, start=1):

            if not page_text or not page_text.strip():
                continue

            start_pos = len(full_text)

            full_text += (
                f"\n\n[[PAGE:{page_number}]]\n"
                f"{page_text}"
            )

            page_boundaries.append(
                {
                    "page_number": page_number,
                    "start": start_pos,
                }
            )

        if not full_text.strip():
            return {"status": "empty"}

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=[
                "\n\n",
                "\n",
                ". ",
                "? ",
                "! ",
                "; ",
                " ",
                ""
            ]
        )

        split_texts = splitter.split_text(full_text)

        if not split_texts:
            return {"status": "empty"}

        chunks = []

        current_search_position = 0

        for chunk_text in split_texts:

            chunk_start = full_text.find(
                chunk_text,
                current_search_position
            )

            if chunk_start == -1:
                chunk_start = current_search_position

            current_search_position = chunk_start

            chunk_page = 1

            for boundary in page_boundaries:
                if boundary["start"] <= chunk_start:
                    chunk_page = boundary["page_number"]
                else:
                    break

            cleaned_chunk = chunk_text
            while "[[PAGE:" in cleaned_chunk:
                start = cleaned_chunk.find("[[PAGE:")
                end = cleaned_chunk.find("]]", start)

                if end == -1:
                    break

                cleaned_chunk = (
                    cleaned_chunk[:start]
                    + cleaned_chunk[end + 2:]
                )

            content = (
                f"[TITULO] {title}\n\n"
                f"[CONTENIDO]\n"
                f"{cleaned_chunk.strip()}"
            )

            chunks.append(
                langchain_Document(
                    page_content=content,
                    metadata={
                        "blob_name": document_data["blob_url"],
                        "document_id": document_id,
                        "content_hash": document_data["content_hash"],
                        "extension": processor.extension(),
                        "user_uid": document_data["user_uid"],
                        "type": processor.document_type(),
                        "creation_datetime": document_data["created_at"].isoformat(),
                        "page_number": chunk_page,
                        "source_url": document_data["source_url"],
                        "title": document_data["title"],
                    }
                )
            )

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

        database.insert_documents_fts(
            documents=chunks,
            ids=ids
        )

        database.update_document_status(
            document_id,
            "READY"
        )

        return {
            "status": "ok",
            "document_id": document_id,
            "hash": document_data["content_hash"]
        }

    except Exception:
        database.update_document_status(
            document_id,
            "ERROR"
        )
        raise