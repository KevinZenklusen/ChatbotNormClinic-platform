---

# Agente Conversacional para consulta de normativa de ingeniería clínica

El backend está construido con **FastAPI** y utiliza **LangGraph** para orquestar la lógica del agente, que puede utilizar modelos tanto locales como online.

---

## Características Principales

-   **Backend con FastAPI**: Expone la lógica del agente a través de una API REST robusta y rápida.
-   **Orquestación con LangGraph**: Gestiona flujos de conversación complejos y la ejecución de herramientas de forma inteligente.
-   **Texto**: Procesamiento de consultas en formato de texto.
-   **Memoria Persistente**: Utiliza **PostgreSQL** para almacenar el historial de conversaciones, permitiendo un diálogo continuo y contextual.
-   **Búsqueda Semántica**: Integrado como una herramienta, utiliza `pgvector` para encontrar información relevante en una base de datos de documentos.
-   **Búsqueda Léxica**: Integrado como una herramienta, utiliza `PostgreSQL` para encontrar información relevante en una base de datos de documentos.
-   **Dockerizado**: Listo para un despliegue sencillo en plataformas como **Hugging Face Spaces**.

---

## Arquitectura del Proyecto

-   `app/main.py`: Punto de entrada de la aplicación FastAPI.
-   `app/routes/agent.py`: Contiene el endpoint principal `/agent/` que recibe las peticiones y orquesta la respuesta del agente.
-   `app/tools/`: Módulos con las funciones que el agente puede ejecutar (búsqueda).
-   `app/core/`: Contiene la configuración central, el cliente de la base de datos, la configuración del LLM y la gestión de la memoria del chat.
-   `app/models/`: Define los esquemas de datos para las peticiones y respuestas.

## Configuración del Proyecto


Siga estos pasos para ejecutar el backend en su entorno local.

### 1. Clonar el Repositorio

```bash
git clone git@github.com:KevinZenklusen/ChatbotNormClinic-platform.git
cd ChatbotNormClinic-platform
```

### 2. Crear y Activar un Entorno Virtual

#### Windows

```bash
python3 -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias

Con el entorno virtual activado, instale las dependencias necesarias:

```bash
pip install -r requirements.txt
```

---

### 4. Configurar las variables de entorno

Las siguentes variables de entorno son requeridas para el correcto funcionamiento del código:

# En caso de querer utilizar Supabase como DB y bucket online
- SUPABASE_URL: URL del proyecto de supabase
- SUPABASE_KEY: API KEY de acceso al proyecto de Supabase

# En caso de querer utilizar GEMINI y/o GROQ como LLMs para el agente
- GEMINI_API_KEY = API KEY de GEMINI
- GEMINI_MODEL = "gemini-3.1-flash-lite"
- GROQ_API_KEY = API KEY de GROQ

# En caso de querer utilizar LLMs locales
- LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
- LM_STUDIO_LOCAL_MODEL_NAME = "LM-Studio-Model"

# Número de documentos recuperados para cada consulta
- RAG_RETRIEVAL_TOP_K = 20
- RAG_FINAL_TOP_K = 10

# Configuración de la DB (puede ser local u online)
- DB_HOST
- DB_PORT
- DB_NAME
- DB_USER
- DB_PASSWORD

# Variables de configuración. Permiten elegir si el funcionamiento es local u online
- STORAGE_MODE = "online" # local | online
- LLM_MODE = "gemini" # local | gemini | groq

# Ruta de almacenamiento local
- LOCAL_STORAGE_PATH

# Ruta de almacenamiento online
- SUPABASE_BUCKET

## 5. Ejecutar la Aplicación

El proyecto corre a través de uvicorn. El puerto es a elección del usuario (En este ejemplo es 8081):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8081
```