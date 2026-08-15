from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import import_, reconciliation, rentabilidade
from app.db.session import init_db


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

app.include_router(import_.router)
app.include_router(rentabilidade.router)
app.include_router(reconciliation.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
