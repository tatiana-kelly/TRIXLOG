from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.viagem_link import ViagemLink

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


class ResolveLinkRequest(BaseModel):
    contrato_transporte_numero: str | None  # null = "sem custo de terceiro identificável"
    resolved_by: str


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)) -> list[dict]:
    """Camada 3 — fila de conciliação manual (docs/COST_ALLOCATION.md#2)."""
    links = db.query(ViagemLink).filter(ViagemLink.status == "pendente").all()
    return [
        {
            "id": link.id,
            "cte_numero": link.cte_numero,
            "candidatos": link.candidatos,
        }
        for link in links
    ]


@router.post("/{link_id}/resolve")
def resolve_link(link_id: str, payload: ResolveLinkRequest, db: Session = Depends(get_db)) -> dict:
    link = db.get(ViagemLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="viagem_link não encontrado")

    link.contrato_transporte_numero = payload.contrato_transporte_numero
    link.metodo_vinculo = "manual"
    link.confianca_vinculo = 1.0
    link.status = "resolvido"
    link.resolved_by = payload.resolved_by
    link.resolved_at = datetime.now(UTC)
    db.commit()
    return {"id": link.id, "status": link.status}
