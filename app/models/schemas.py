from pydantic import BaseModel

from app.core.config import RAG_RETRIEVAL_TOP_K

class BusquedaRequest(BaseModel):
    consulta: str
    session_id: str
    user_id: str


class DocumentoBusquedaRequest(BaseModel):
    consulta: str
    top_k: int = RAG_RETRIEVAL_TOP_K