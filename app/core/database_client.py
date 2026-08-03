from app.core.config import DB_CONFIG
from langchain_community.vectorstores import PGVector
from langchain_community.vectorstores.pgvector import DistanceStrategy
import psycopg2
from psycopg2.errors import UniqueViolation
import json
import csv


class Database:

    def __init__(self, db_config):
        self.db_config = db_config
        self._vectorstores = {} 

    def _conn(self):
        return psycopg2.connect(
            host=self.db_config["host"],
            port=self.db_config["port"],
            dbname=self.db_config["database"],
            user=self.db_config["user"],
            password=self.db_config["password"],
        )
                                                                                                                               
    def ensure_tables_exist(self):
        with self._conn() as conn, conn.cursor() as cur:

            # Tabla chat_history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.chat_history (
                    session_id TEXT PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    history JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Tabla documents
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.documents (
                    id TEXT PRIMARY KEY,
                    user_uid TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    blob_url TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    UNIQUE (user_uid, content_hash)
                );
            """)
            
            # Tablas/Funciones de búsqueda léxica
            # ---------------- documents_fts ----------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.documents_fts (
                    id TEXT PRIMARY KEY,
                    document_id TEXT,
                    chunk_id TEXT,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    content_tsv tsvector
                );
            """)

            # ---------------- índice GIN ----------------
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_fts_tsv
                ON public.documents_fts
                USING GIN (content_tsv);
            """)

            # ---------------- función trigger ----------------
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_documents_fts_tsv()
                RETURNS trigger AS $$
                BEGIN
                  NEW.content_tsv := to_tsvector('spanish', NEW.content);
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # ---------------- trigger ----------------
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger 
                        WHERE tgname = 'tsvector_update_documents_fts'
                    ) THEN
                        CREATE TRIGGER tsvector_update_documents_fts
                        BEFORE INSERT OR UPDATE
                        ON public.documents_fts
                        FOR EACH ROW
                        EXECUTE FUNCTION update_documents_fts_tsv();
                    END IF;
                END$$;
            """)

            conn.commit()

    
    # ---------- documentos --------
                                                        
    def document_exists(self, *, user_uid: str, content_hash: str) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, blob_url, created_at
                FROM documents
                WHERE user_uid = %s AND content_hash = %s
                """,
                (user_uid, content_hash)
            )
            row = cur.fetchone()
            if not row:
                return None

            return {
                "document_id": row[0],
                "blob_url": row[1],
                "created_at": row[2]
            }

    def insert_document_data(
        self,
        *,
        document_id: str,
        user_uid: str,
        content_hash: str,
        blob_url: str,
        source_url: str,
        created_at,
        status: str,
        title: str
    ):
        try:
            with self._conn() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (
                        id,
                        user_uid,
                        content_hash,
                        blob_url,
                        source_url,
                        created_at,
                        status,
                        title
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        user_uid,
                        content_hash,
                        blob_url,
                        source_url,
                        created_at,
                        status,
                        title
                    )
                )
                conn.commit()

        except UniqueViolation:
            raise
    
    def get_document_data(self, document_id: str) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    user_uid,
                    content_hash,
                    blob_url,
                    source_url,
                    created_at,
                    title
                FROM documents
                WHERE id = %s
                """,
                (document_id,)
            )
            row = cur.fetchone()

            if not row:
                return None

            return {
                "document_id": row[0],
                "user_uid": row[1],
                "content_hash": row[2],
                "blob_url": row[3],
                "source_url": row[4],
                "created_at": row[5],
                "title": row[6]
            }
        
    def update_document_status(self, document_id: str, status: str):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET status = %s
                WHERE id = %s
                """,
                (status, document_id)
            )
            conn.commit()

    def get_document_by_source_url(self, user_uid: str, source_url: str) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    user_uid,
                    content_hash,
                    blob_url,
                    source_url,
                    created_at,
                    status,
                    title
                FROM documents
                WHERE user_uid = %s AND source_url = %s
                """,
                (user_uid, source_url)
            )

            row = cur.fetchone()

            if not row:
                return None

            return {
                "document_id": row[0],
                "user_uid": row[1],
                "content_hash": row[2],
                "blob_url": row[3],
                "source_url": row[4],
                "created_at": row[5],
                "status": row[6],
                "title": row[7]
            }
        
    def update_document_content(
        self,
        *,
        document_id: str,
        content_hash: str,
        blob_url: str
    ):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET content_hash = %s,
                    blob_url = %s
                WHERE id = %s
                """,
                (content_hash, blob_url, document_id)
            )
            conn.commit()


    # ---------- Búsqueda léxica --------
    def _extract_lexemes(self, cur, query: str) -> list[str]:
        """Convierte una consulta libre en los lexemas
        que PostgreSQL genera usando el diccionario spanish.
        """

        cur.execute(
            """
            SELECT plainto_tsquery('spanish', %s)::text
            """,
            (query,)
        )

        tsquery_text = cur.fetchone()[0]

        if not tsquery_text:
            return []

        lexemes = []

        for token in tsquery_text.split("&"):
            token = token.strip().replace("'", "")

            if token:
                lexemes.append(token)

        return lexemes

    def insert_documents_fts(self, documents, ids):
        """
        Guarda chunks en tabla FTS.
        ids → deben ser los mismos que usás en embeddings
        """
        with self._conn() as conn, conn.cursor() as cur:

            for doc, id_ in zip(documents, ids):
                cur.execute(
                    """
                    INSERT INTO documents_fts (
                        id,
                        document_id,
                        chunk_id,
                        content,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        id_,
                        doc.metadata.get("document_id"),
                        id_,
                        doc.page_content,
                        json.dumps(doc.metadata)
                    )
                )

            conn.commit()

    def lexical_search(
        self,
        query: str,
        top_k: int,
        document_ids=None
    ):

        with self._conn() as conn, conn.cursor() as cur:

            lexemes = self._extract_lexemes(cur, query)

            if not lexemes:
                return []

            score_parts = []
            params = []

            for lexeme in lexemes:
                score_parts.append(
                    "(content_tsv @@ to_tsquery('spanish', %s))::int"
                )
                params.append(lexeme)

            score_expr = " + ".join(score_parts)

            total_terms = len(lexemes)

            sql = f"""
            SELECT
                content,
                metadata,
                ({score_expr}) AS match_count,
                (
                    ({score_expr})::float
                    / %s
                ) AS normalized_score
            FROM documents_fts
            WHERE
                ({score_expr}) >= %s
            """

            query_params = []

            # SELECT match_count
            query_params.extend(params)

            # SELECT normalized_score
            query_params.extend(params)

            query_params.append(total_terms)

            # WHERE
            query_params.extend(params)

            query_params.append(2)  # mínimo 2 coincidencias

            if document_ids:
                sql += " AND document_id = ANY(%s)"
                query_params.append(document_ids)

            sql += """
            ORDER BY normalized_score DESC
            LIMIT %s
            """

            query_params.append(top_k)

            cur.execute(sql, query_params)

            rows = cur.fetchall()

        resultados = []

        for row in rows:
            resultados.append(
                {
                    "text": row[0],
                    "metadata": row[1],
                    "match_count": int(row[2]),
                    "score": float(row[3]),
                    "source": "lexical"
                }
            )

        return resultados
        
    # ---------- vectores ----------
                                                                       
    def _get_vectorstore(self,collection_name: str,embedding_function) -> PGVector:
        if collection_name not in self._vectorstores:
            connection_string = PGVector.connection_string_from_db_params(
                driver="psycopg2",
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
            )
            self._vectorstores[collection_name] = PGVector(
                connection_string=connection_string,
                collection_name=collection_name,
                embedding_function=embedding_function,
                distance_strategy=DistanceStrategy.COSINE
            )
        return self._vectorstores[collection_name]


    def create_and_store_embeddings(self, collection_name, documents, embedding_function, ids):
        store = self._get_vectorstore(collection_name, embedding_function)
        store.add_documents(
            documents=documents,
            ids=ids
        )

    def search(self, collection_name, query: str, embedding_function, top_k: int):
        store = self._get_vectorstore(collection_name, embedding_function)
        docs_and_scores = store.similarity_search_with_score(
            query=query,
            k=top_k
        )

        resultados = []
        for doc, score in docs_and_scores:
            resultados.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
                "source": "semantic"
            })

        return resultados
        
    def delete_embeddings(self, document_id: str):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM langchain_pg_embedding
                WHERE custom_id LIKE %s
                """,
                (f"{document_id}%",)
            )
            conn.commit()

    # ---------- chat history ----------                     
                                                        
    def get_chat_history(self, session_id: str) -> list:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT history FROM chat_history WHERE session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
            return row[0] if row else []

    def save_chat_history(self, session_id: str, history: list):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (session_id, history, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (session_id)
                DO UPDATE SET history = EXCLUDED.history,
                              updated_at = now()
                """,
                (session_id, json.dumps(history))
            )
            conn.commit()

    def delete_chat_history(self, session_id: str):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_history WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()

    def append_chat_history(self, user_id: str, session_id: str, new_messages: list):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (user_id, session_id, history, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (session_id)
                DO UPDATE SET
                    history = chat_history.history || EXCLUDED.history,
                    updated_at = now()
                """,
                (user_id, session_id, json.dumps(new_messages))
            )
            conn.commit()

    # Función auxiliar para agregar titulo a los documentos en caso de que no lo tengan
    def add_title_to_documents(self):

        titles = []

        with open("document_titles.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                titles.append({
                    "url": row["url"],
                    "title": row["title"]
                })
        
            existing_urls = set()

            with self._conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT source_url FROM documents;")
                for row in cur.fetchall():
                    existing_urls.add(row[0])

                missing_in_db = []
                valid_rows = []

                for item in titles:
                    if item["url"] in existing_urls:
                        valid_rows.append(item)
                    else:
                        missing_in_db.append(item["url"])

                print("URLs encontradas en DB:", len(valid_rows))
                print("URLs faltantes en DB:", len(missing_in_db))

                if missing_in_db:
                    print("\nFaltantes:")
                    for url in missing_in_db:
                        print(url)


                print("\nActualizando títulos...")

                for item in valid_rows:
                    cur.execute(
                        """
                        UPDATE documents
                        SET title = %s
                        WHERE source_url = %s
                        """,
                        (item["title"], item["url"])
                    )

                conn.commit()

                print("Update terminado")




def _create_database() -> Database:
    return Database(DB_CONFIG)


database: Database = _create_database()


