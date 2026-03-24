from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routes import agent, documentos, normativa
from app.core.database_client import database


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

FILES_DIR = PROJECT_ROOT / "files"

FILES_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.ensure_tables_exist()
    yield

app = FastAPI(lifespan=lifespan)

app.mount(
    "/files",
    StaticFiles(directory=FILES_DIR),
    name="files"
)

app.include_router(agent.router, prefix="/agent")
app.include_router(documentos.router, prefix="/documents")
app.include_router(normativa.router, prefix="/sync_normativa")