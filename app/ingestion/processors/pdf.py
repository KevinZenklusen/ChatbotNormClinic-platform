from typing import List
import fitz

from app.ingestion.processors.base import BaseDocumentProcessor


class PDFProcessor(BaseDocumentProcessor):

    def extract_pages(self, content: bytes) -> List[str]:
        pages: List[str] = []

        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    pages.append(text)

        return pages

    def document_type(self) -> str:
        return "PDF"

    def extension(self) -> str:
        return "pdf"