from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


class ResolveLinkRequest(BaseModel):
    contrato_transporte_numero: str | None  # null = "sem custo de terceiro identificável"
    resolved_by: str


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)) -> list[dict]:
    """Camada 3 — fila de conciliação manual (docs/COST_ALLOCATION.md#2). Junta com CTe para dar
    contexto real ao operador (cliente, mês, unidade) — cte_numero sozinho é ambíguo entre meses.

    Busca tudo em lote (CTe's e Contratos de uma vez, não um SELECT por link/candidato) — um N+1
    aqui é invisível no SQLite local (latência zero) mas trava contra Postgres remoto assim que a
    fila cresce (confirmado: 115 pendentes = centenas de round-trips de rede, timeout real)."""
    links = db.query(ViagemLink).filter(ViagemLink.status == "pendente").all()

    cte_ids = {link.cte_id for link in links}
    ctes_por_id = {c.id: c for c in db.query(CTe).filter(CTe.id.in_(cte_ids)).all()} if cte_ids else {}

    todos_contratos = db.query(ContratoTransporte).all()
    contratos_por_chave = {(c.contrato_numero, c.unidade): c for c in todos_contratos}

    out = []
    for link in links:
        cte = ctes_por_id.get(link.cte_id)
        candidatos_detalhados = []
        for numero in link.candidatos:
            contrato = contratos_por_chave.get((numero, cte.unidade if cte else None))
            candidatos_detalhados.append(
                {
                    "contrato_numero": numero,
                    "fornecedor_nome": contrato.fornecedor_nome if contrato else None,
                    "valor_total_contrato": float(contrato.valor_total_contrato) if contrato else None,
                }
            )
        out.append(
            {
                "id": link.id,
                "cte_numero": link.cte_numero,
                "cliente": cte.pagador_frete_nome if cte else None,
                "unidade": cte.unidade if cte else None,
                "mes_referencia": cte.data_emissao.strftime("%Y-%m") if cte and cte.data_emissao else None,
                "receita": float(cte.total) if cte else None,
                "candidatos": candidatos_detalhados,
            }
        )
    return out


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
