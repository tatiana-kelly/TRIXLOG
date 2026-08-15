from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.monthly_analytics import (
    comparativo_mensal,
    detectar_desvios_mensais,
    listar_meses_disponiveis,
    rentabilidade_mensal_por_cliente,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/meses")
def meses_disponiveis(db: Session = Depends(get_db)) -> list[str]:
    """Meses com dado importado — alimenta o filtro mensal da plataforma."""
    return listar_meses_disponiveis(db)


@router.get("/rentabilidade-mensal")
def rentabilidade_mensal(mes: str, unidade: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Rentabilidade por cliente num mês específico (YYYY-MM), opcionalmente filtrada por unidade."""
    itens = rentabilidade_mensal_por_cliente(db, mes_referencia=mes, unidade=unidade)
    return [
        {
            "cliente": i.cliente,
            "receita_total": i.receita_total,
            "custo_alocado_total": i.custo_alocado_total,
            "margem_total": i.margem_total,
            "viagens_com_custo_alocado": i.viagens_com_custo_alocado,
            "viagens_pendentes": i.viagens_pendentes,
            "pct_custo_nao_alocado": i.pct_custo_nao_alocado,
        }
        for i in itens
    ]


@router.get("/comparativo")
def comparativo(meses: str, unidade: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Comparativo mês a mês por cliente. `meses` = lista separada por vírgula, ex.: 2026-05,2026-06,2026-07."""
    lista_meses = [m.strip() for m in meses.split(",") if m.strip()]
    itens = comparativo_mensal(db, lista_meses, unidade=unidade)
    return [
        {
            "cliente": c.cliente,
            "por_mes": {
                mes: {
                    "receita_total": v.receita_total,
                    "custo_alocado_total": v.custo_alocado_total,
                    "margem_total": v.margem_total,
                    "pct_custo_nao_alocado": v.pct_custo_nao_alocado,
                }
                for mes, v in c.por_mes.items()
            },
        }
        for c in itens
    ]


@router.get("/desvios")
def desvios(mes_atual: str, mes_anterior: str, unidade: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Desvios materiais de receita por cliente entre dois meses (FATO/CÁLCULO — causa provável
    é trabalho do Investigador, não deste endpoint)."""
    itens = detectar_desvios_mensais(db, mes_atual=mes_atual, mes_anterior=mes_anterior, unidade=unidade)
    return [
        {
            "cliente": d.cliente,
            "mes_atual": d.mes_atual,
            "mes_anterior": d.mes_anterior,
            "receita_atual": d.receita_atual,
            "receita_anterior": d.receita_anterior,
            "variacao_absoluta": d.variacao_absoluta,
            "variacao_percentual": d.variacao_percentual,
            "tipo": d.tipo,
        }
        for d in itens
    ]
