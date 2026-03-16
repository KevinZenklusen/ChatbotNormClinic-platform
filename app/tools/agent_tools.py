from langchain_core.tools import tool
from sentence_transformers.cross_encoder import CrossEncoder
from app.services.busqueda import buscar_documentos
from app.models.schemas import BusquedaRequest
import json

from app.core.config import RAG_RETRIEVAL_TOP_K, RAG_FINAL_TOP_K

cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

@tool
def buscar_contexto_en_documentos(consulta: str) -> str:
    """
    Útil para buscar información en documentos.
    Devuelve contexto relevante junto con metadata estructurada.
    """

    print(f"--- Herramienta RAG buscando contexto para: {consulta} ---")

    payload_busqueda = BusquedaRequest(consulta=consulta, top_k=RAG_RETRIEVAL_TOP_K)
    resultado_busqueda = buscar_documentos(payload_busqueda)

    if not resultado_busqueda.get("resultados"):
        return json.dumps({
            "contexto_llm": "No se encontró contexto relevante en los documentos.",
            "sources": []
        })

    chunks = resultado_busqueda["resultados"]

    pares_para_rerank = [[consulta, chunk["text"]] for chunk in chunks]
    puntajes = cross_encoder.predict(pares_para_rerank)

    for i, chunk in enumerate(chunks):
        chunk["relevance_score"] = float(puntajes[i])

    chunks_reordenados = sorted(
        chunks,
        key=lambda x: x["relevance_score"],
        reverse=True
    )

    contexto_final_chunks = chunks_reordenados[:RAG_FINAL_TOP_K]

    contexto_para_llm = "\n\n".join(
            chunk["text"] for chunk in contexto_final_chunks
        )

    metadata_structurada = [
        {
            "source_url": chunk["metadata"].get("source_url"),
            "blob_name": chunk["metadata"].get("blob_name"),
            "page_number": chunk["metadata"].get("page_number"),
            "document_id": chunk["metadata"].get("document_id"),
        }
        for chunk in contexto_final_chunks
    ]

    return json.dumps({
        "contexto_llm": contexto_para_llm,
        "sources": metadata_structurada
    })