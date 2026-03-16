# app/core/llm_config.py

# Importar la clase base de LangChain para tipado genérico
from langchain_core.language_models import BaseChatModel 

# --- Importaciones de Proveedores ---
# Opción 1: Google (Mantenerla para fácil cambio)
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import GEMINI_API_KEY, LM_STUDIO_BASE_URL, LM_STUDIO_LOCAL_MODEL_NAME, LLM_MODE, GROQ_API_KEY
# Opción 2: LLM Local (LM Studio usa la API de OpenAI)
from langchain_openai import ChatOpenAI
# Opción 3: Groq (Online)
from langchain_groq import ChatGroq
import os
# --- Fin de Importaciones ---

# Configuración de la API Local de LM Studio (en caso de usarlo)


def get_llm() -> BaseChatModel:
    """
    Inicializa y retorna la instancia del LLM. 
    """
    print(LLM_MODE)

    if LLM_MODE == "gemini":
    
        # -----------------------------------------------------------
        # 1. Configuración de Google Gemini (Opción Remota)
        # -----------------------------------------------------------
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=GEMINI_API_KEY
        )
        print("LLM: Gemini")

    elif LLM_MODE == "local":

        # -----------------------------------------------------------
        # 2. Configuración de LLM Local (LM Studio usando ChatOpenAI)
        # -----------------------------------------------------------
        
        llm = ChatOpenAI(
            model=LM_STUDIO_LOCAL_MODEL_NAME, 
            base_url=LM_STUDIO_BASE_URL, 
            api_key="lm-studio", # El API key no es necesario si se usa en local, pero LangChain lo espera. Se puede usar un string cualquiera.
            # temperature=1,
        )
        print("LLM: Local")
    
    elif LLM_MODE == "groq":
        
        # -----------------------------------------------------------
        # 3. Configuración de Groq (Opción remota)
        # -----------------------------------------------------------

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY
        )
        print("LLM: Groq")
    
    return llm

def get_guardian_llm():
    
    guardian_llm = ChatGroq(
        model="openai/gpt-oss-safeguard-20b",
        api_key=GROQ_API_KEY
    )
    
    return guardian_llm

llm = get_llm()
guardian_llm = get_guardian_llm()