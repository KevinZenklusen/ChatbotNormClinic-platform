from sentence_transformers import SentenceTransformer
from langchain_community.embeddings import HuggingFaceEmbeddings

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def generar_embedding(texto: str) -> list[float]:
    return model.encode(texto).tolist()

def obtener_modelo_de_embeddings() -> HuggingFaceEmbeddings:
    modelo_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    return modelo_embeddings