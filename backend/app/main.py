from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analytics, import_, reconciliation, rentabilidade
from app.db.session import init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TRIXLOG Torre de Controle",
    description="Rentabilidade por cliente/viagem a partir dos relatórios reais — sem chave de alocação de custo inventada.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_.router)
app.include_router(rentabilidade.router)
app.include_router(reconciliation.router)
app.include_router(analytics.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))
