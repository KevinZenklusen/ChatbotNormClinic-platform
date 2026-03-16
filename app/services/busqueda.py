from app.core.embedding import obtener_modelo_de_embeddings
from app.core.database_client import database
from app.models.schemas import BusquedaRequest

COLLECTION_NAME = "documents"


def expand_query(query: str) -> list[str]:

    queries = [query]
    queries.append(f"características de {query}")
    queries.append(f"requisitos de {query}")
    queries.append(f"propiedades de {query}")
    queries = list(dict.fromkeys(queries))

    return queries


def buscar_documentos(payload: BusquedaRequest):

    embedding_model = obtener_modelo_de_embeddings()

    queries = expand_query(payload.consulta)

    resultados_totales = []

    for query in queries:
        resultados = database.search(
            collection_name=COLLECTION_NAME,
            query=query,
            embedding_function=embedding_model,
            top_k=payload.top_k
        )

        resultados_totales.extend(resultados)

    # deduplicar por contenido
    seen = set()
    resultados_unicos = []

    for doc in resultados_totales:
        contenido = doc.page_content.strip()

        if contenido not in seen:
            seen.add(contenido)
            resultados_unicos.append(doc)

    return {
        "resultados": [
            {
                "text": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in resultados_unicos
        ]
    }