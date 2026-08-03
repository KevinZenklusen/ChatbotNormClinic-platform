from langchain_core.tools import tool
from sentence_transformers.cross_encoder import CrossEncoder

from app.services.busqueda import buscar_documentos
from app.models.schemas import DocumentoBusquedaRequest
           

from app.core.config import RAG_RETRIEVAL_TOP_K, RAG_FINAL_TOP_K

cross_encoder = CrossEncoder("jinaai/jina-reranker-v2-base-multilingual", trust_remote_code=True)
#cross-encoder/ms-marco-MiniLM-L-6-v2       
# BSC-NLP4BIA/Medprocner-CE-Reranker                              

ALPHA = 0.8


@tool(response_format="content_and_artifact")
def buscar_contexto_en_documentos(consulta: str):
    """
    Busca información en documentos.

    Retorna:
    - content: contexto para el LLM
    - artifact: metadata para el backend/frontend
    """

    print(f"--- Herramienta RAG buscando contexto para: {consulta} ---")

    payload_busqueda = DocumentoBusquedaRequest(
        consulta=consulta,
        top_k=RAG_RETRIEVAL_TOP_K
    )

    resultado_busqueda = buscar_documentos(payload_busqueda)

    if not resultado_busqueda.get("resultados"):
        return (
            "No se encontró contexto relevante en los documentos.",
            {
                "sources": []
            }
        )

    chunks = resultado_busqueda["resultados"]
                    
    with open("chunks.txt", "w", encoding="utf-8") as archivo:
        archivo.write(str(chunks))              

    # Reranking
    pares_para_rerank = [
        [consulta, chunk["text"]]
        for chunk in chunks
    ]

    puntajes = cross_encoder.predict(pares_para_rerank)

    for i, chunk in enumerate(chunks):

        cross_score = float(puntajes[i])
        hybrid_score = float(chunk.get("score", 0))

        chunk["final_score"] = (
            ALPHA * cross_score
            + (1 - ALPHA) * hybrid_score
        )

        chunk["relevance_score"] = cross_score

    chunks_reordenados = sorted(
        chunks,
        key=lambda x: x["final_score"],
        reverse=True
    )

    with open("chunks_reordenados.txt", "w", encoding="utf-8") as archivo:
        archivo.write(str(chunks_reordenados))  

    contexto_final_chunks = chunks_reordenados[:RAG_FINAL_TOP_K]

    fragmentos_llm = []

    for chunk in contexto_final_chunks:

        source_url = chunk["metadata"].get("source_url", "")

        fragmento = f"""
    [SOURCE_URL]
    {source_url}

    {chunk["text"]}
    """

        fragmentos_llm.append(fragmento)

    contexto_para_llm = "\n\n".join(fragmentos_llm)
    
    contexto_para_llm = f"""
    IMPORTANTE:

    Los fragmentos recuperados tienen la siguiente estructura:

    [SOURCE_URL]
    URL del documento original.(Puede contener información sobre el año de publicación. Ej: '123-2011' corresponde al año 2011)

    [TITULO]
    Nombre del documento, norma, capítulo o sección. (Puede contener información sobre el año de publicación. Ej: '934/2001' corresponde al año 2001)

    [CONTENIDO]
    Texto relevante recuperado del documento.
    
    Al responder:

    - Considerá el TITULO como parte del contexto.
    - Considerá la SOURCE_URL como parte del contexto.
    - Si la URL, el título o el contenido indican años, versiones o resoluciones distintas, tené en cuenta la posible vigencia temporal.
    - Ante información contradictoria, priorizá la norma o resolución más reciente cuando el contexto permita identificar la fecha.
    - Si no es posible determinar la vigencia con certeza, indicá que existen fuentes con información diferente y mencioná ambas.

    FRAGMENTOS RECUPERADOS:

    {contexto_para_llm}
    """
                          
    metadata_structurada = [
        {
            "source_url": chunk["metadata"].get("source_url"),
            "blob_name": chunk["metadata"].get("blob_name"),
            "page_number": chunk["metadata"].get("page_number"),
            "document_id": chunk["metadata"].get("document_id"),
        }
        for chunk in contexto_final_chunks
    ]

    return (
        contexto_para_llm,
        {
            "sources": metadata_structurada
        }
    )