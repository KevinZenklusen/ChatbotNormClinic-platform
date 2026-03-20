---
title: ChatbotNormClinic Platform
emoji: 🏢
colorFrom: purple
colorTo: pink
sdk: docker
pinned: false
license: mit
---

# Agente Conversacional para consulta de normativa de ingeniería clínica

El backend está construido con **FastAPI** y utiliza **LangGraph** para orquestar la lógica del agente, que se apoya en los modelos de **Google Gemini** para sus capacidades multimodales.

---

## 🚀 Características Principales

-   **Backend con FastAPI**: Expone la lógica del agente a través de una API REST robusta y rápida.
-   **Orquestación con LangGraph**: Gestiona flujos de conversación complejos y la ejecución de herramientas de forma inteligente.
-   **Capacidades Multimodales**:
    -   **Texto**: Procesamiento de consultas en formato de texto.
-   **Memoria Persistente**: Utiliza **Supabase (PostgreSQL)** para almacenar el historial de conversaciones, permitiendo un diálogo continuo y contextual.
-   **Búsqueda Semántica**: Integrado como una herramienta, utiliza `pgvector` para encontrar información relevante en una base de datos de documentos.
-   **Dockerizado**: Listo para un despliegue sencillo en plataformas como **Hugging Face Spaces**.

---

## 🏗️ Arquitectura del Proyecto

-   `app/main.py`: Punto de entrada de la aplicación FastAPI.
-   `app/routes/agent.py`: Contiene el endpoint principal `/agent/` que recibe las peticiones y orquesta la respuesta del agente.
-   `app/tools/`: Módulos con las funciones que el agente puede ejecutar (búsqueda).
-   `app/services/`: Servicios auxiliares, como el `tts_service` para la conversión de texto a voz.
-   `app/core/`: Contiene la configuración central, el cliente de Supabase, la configuración del LLM y la gestión de la memoria del chat.
-   `app/models/`: Define los esquemas de datos (Pydantic) para las peticiones y respuestas.

---