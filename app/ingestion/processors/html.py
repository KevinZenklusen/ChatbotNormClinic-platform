# ingestion/processors/html.py

from typing import List
from bs4 import BeautifulSoup

from app.ingestion.processors.base import BaseDocumentProcessor


class HTMLProcessor(BaseDocumentProcessor):

    def extract_pages(self, content: bytes) -> List[str]:
        html = content.decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        text = "\n".join(
            line.strip() for line in text.splitlines() if line.strip()
        )

        if not text:
            return []

        return [text]

    def document_type(self) -> str:
        return "HTML"

    def extension(self) -> str:
        return "html"
