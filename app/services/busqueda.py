import json
import re

from app.core.llm_config import llm
from app.core.embedding import obtener_modelo_de_embeddings
from app.core.database_client import database
from app.models.schemas import BusquedaRequest
import spacy

nlp = spacy.load("es_core_news_md")

COLLECTION_NAME = "documents"


def extract_text_from_response(response) -> str:
    if isinstance(response.content, str):
        return response.content

    if isinstance(response.content, list):
        texts = []
        for item in response.content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)

    return str(response.content)


def expand_query(query: str) -> list[str]:

    prompt = f"""
        Generá 3 queries de búsqueda CORTAS (no más de 10 palabras) para mejorar un sistema RAG.

        Consulta:
        "{query}"

        Devolvé cada query en una línea separada.
        NO uses numeración.
        NO agregues explicaciones.
        Si encontrás siglas/acrónicos (Ejemplo: SRL = Sociedad de Responsabilidad Limitada) en lo posible usá el significado del acrónimo
        """

    response = llm.invoke(prompt)
    content = extract_text_from_response(response)

    try:
        try:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                queries = json.loads(match.group(0))
                return list(dict.fromkeys([query] + queries[:6]))
        except:
            pass

        lines = content.split("\n")

        queries = []
        for line in lines:
            line = line.strip()

            line = re.sub(r"^\d+[\.\)]\s*", "", line)

            if len(line) > 5:
                queries.append(line)

        if not queries:
            return [query]

        return list(dict.fromkeys([query] + queries[:6]))

    except Exception as e:
        print("Expansion error:", e)
        return [query]


def diversify_by_document(results, max_per_doc=2):
    grouped = {}
    final = []

    for doc in results:
        doc_id = doc["metadata"].get("document_id", "unknown")

        if doc_id not in grouped:
            grouped[doc_id] = []

        if len(grouped[doc_id]) < max_per_doc:
            grouped[doc_id].append(doc)
            final.append(doc)

    return final


def normalize_query_for_fts(query: str) -> str:
    doc = nlp(query.lower())

    tokens = []

    for token in doc:
        if token.is_stop:
            continue
        if token.is_punct:
            continue
        if len(token.lemma_) <= 2:
            continue

        tokens.append(token.lemma_)

    return " ".join(tokens)


def get_relevant_documents(query: str, top_k=20):

    clean_query = normalize_query_for_fts(query)

    with database._conn() as conn, conn.cursor() as cur:

        cur.execute(
            """
            SELECT
                document_id,
                MAX(
                    ts_rank_cd(
                        content_tsv,
                        websearch_to_tsquery('spanish', %s)
                    )
                ) AS score
            FROM documents_fts
            WHERE content_tsv @@ websearch_to_tsquery('spanish', %s)
            GROUP BY document_id
            ORDER BY score DESC
            LIMIT %s
            """,
            (
                clean_query,
                clean_query,
                top_k
            )
        )

        rows = cur.fetchall()

    return [row[0] for row in rows]



def reciprocal_rank_fusion(results, k=60):

    SEMANTIC_WEIGHT = 0.5
    LEXICAL_WEIGHT = 0.5

    scores = {}

    for result_set in results:
        for rank, doc in enumerate(result_set):
         
            key = (
                doc["metadata"].get("document_id"),
                doc["text"]
            )

            if key not in scores:
                scores[key] = {
                    "doc": doc,
                    "score": 0
                }

            # weighting
            if doc.get("source") == "semantic":
                weight = SEMANTIC_WEIGHT
            else:
                weight = LEXICAL_WEIGHT

            scores[key]["score"] += weight * (
                (1 / (k + rank + 1))
                + 0.05 * doc.get("score", 0)
            )

    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    return [item["doc"] for item in ranked]


def buscar_documentos(payload: BusquedaRequest):

    embedding_model = obtener_modelo_de_embeddings()
    queries = expand_query(payload.consulta)

    doc_ids = []

    for q in queries:
        docs = get_relevant_documents(q)
        doc_ids.extend(docs)

    doc_ids = list(dict.fromkeys(doc_ids))

    semantic_results = []
    lexical_results = []

    for query in queries:

        # búsqueda semántica
        semantic_results.append(
            database.search(
                collection_name=COLLECTION_NAME,
                query=query,
                embedding_function=embedding_model,
                top_k=payload.top_k * 2
            )
        )

        # búsqueda léxica      
        lexical_results.append(
            database.lexical_search(
                query=normalize_query_for_fts(query),
                top_k=payload.top_k * 2,
                document_ids=doc_ids
            )
        )

    # fusionar búsqueda
    fused_results = reciprocal_rank_fusion(
        semantic_results + lexical_results
    )

    fused_results = diversify_by_document(fused_results, max_per_doc=7)

    # deduplicación
    seen = set()
    resultados_unicos = []

    for doc in fused_results:
        contenido = doc["text"].strip()

        if contenido not in seen:
            seen.add(contenido)
            resultados_unicos.append(doc)

    return {
        "resultados": [
            {
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": doc.get("score"),
                "source": doc.get("source")
            }
            for doc in resultados_unicos
        ]
    }