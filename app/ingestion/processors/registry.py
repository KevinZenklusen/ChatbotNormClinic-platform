from app.ingestion.processors.pdf import PDFProcessor
from app.ingestion.processors.html import HTMLProcessor


PROCESSOR_REGISTRY = {
    "application/pdf": PDFProcessor,
    "text/html": HTMLProcessor,
}


def get_processor(content_type: str):
    processor_cls = PROCESSOR_REGISTRY.get(content_type)

    if not processor_cls:
        raise ValueError(f"No processor for content_type={content_type}")

    return processor_cls()