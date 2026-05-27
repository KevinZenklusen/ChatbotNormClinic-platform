from app.core.config import DB_CONFIG
from langchain_community.vectorstores import PGVector
from langchain_community.vectorstores.pgvector import DistanceStrategy
import psycopg2
from psycopg2.errors import UniqueViolation
import json

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
                    history JSONB,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
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
                    UNIQUE (user_uid, content_hash)
                );
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
        status: str
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
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        user_uid,
                        content_hash,
                        blob_url,
                        source_url,
                        created_at,
                        status
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
                    created_at
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
                    status
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
        return store.similarity_search(
            query=query,
            k=top_k
        )
    
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

    def append_chat_history(self, session_id: str, new_messages: list):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (session_id, history, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (session_id)
                DO UPDATE SET
                    history = chat_history.history || EXCLUDED.history,
                    updated_at = now()
                """,
                (session_id, json.dumps(new_messages))
            )
            conn.commit()


def _create_database() -> Database:
    return Database(DB_CONFIG)

database: Database = _create_database()


