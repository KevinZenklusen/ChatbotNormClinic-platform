import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "ChatClinic"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "postgres")
}

RAG_RETRIEVAL_TOP_K = int(os.getenv("RAG_RETRIEVAL_TOP_K", 10))
RAG_FINAL_TOP_K = int(os.getenv("RAG_FINAL_TOP_K", 3))

# LLM
LLM_MODE = os.getenv("LLM_MODE", "local")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LM_STUDIO_LOCAL_MODEL_NAME = os.getenv('LM_STUDIO_LOCAL_MODEL_NAME')
LM_STUDIO_BASE_URL = os.getenv('LM_STUDIO_BASE_URL')

# Web Scrapping
BASE_URL = "http://leg.msal.gov.ar/atlas/calidad_garantia.html"
ALLOWED_DOMAINS = [
    "leg.msal.gov.ar",
    "e-legis-ar.msal.gov.ar"
]

# Almacenamiento
STORAGE_MODE= os.getenv("STORAGE_MODE", "local")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./files")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "documents")
