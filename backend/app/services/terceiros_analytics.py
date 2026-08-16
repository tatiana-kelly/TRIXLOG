"""Rentabilidade de frete terceiro/agregado — PRP da Tatiana seção 23. Complementar a
fleet_analytics.py: aqui é "quem operou" (transportador/proprietário terceiro), lá é "que placa
própria operou". Exclui as placas de frota própria (mesma lista de fleet_analytics.py) — nunca
mistura os dois universos."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.services.custo_lookup import custo_confirmado_por_cte
from app.services.fleet_analytics import DONOS_FROTA_PROPRIA


@dataclass
class RentabilidadeTerceiro:
    proprietario: str
    qtd_ctes: int = 0
    receita_total: float = 0.0
    custo_alocado_total: float = 0.0
    margem_total: float = 0.0
    viagens_com_custo_alocado: int = 0
    viagens_pendentes: int = 0


def calcular_rentabilidade_por_terceiro(
    db: Session, mes_referencia: str | None = None, unidade: str | None = None
) -> list[RentabilidadeTerceiro]:
    query = db.query(CTe)
    if unidade:
        query = query.filter(CTe.unidade == unidade)
    ctes = query.all()
    if mes_referencia:
        ctes = [c for c in ctes if c.data_emissao and c.data_emissao.strftime("%Y-%m") == mes_referencia]

    ctes_terceiro = [
        c for c in ctes if c.proprietario_veiculo_nome and c.proprietario_veiculo_nome not in DONOS_FROTA_PROPRIA
    ]
    custo_por_cte = custo_confirmado_por_cte(db, ctes_terceiro)

    por_terceiro: dict[str, RentabilidadeTerceiro] = {}
    for cte in ctes_terceiro:
        bucket = por_terceiro.setdefault(
            cte.proprietario_veiculo_nome, RentabilidadeTerceiro(proprietario=cte.proprietario_veiculo_nome)
        )
        bucket.qtd_ctes += 1
        bucket.receita_total += float(cte.total)
        custo = custo_por_cte.get(cte.id)
        if custo is not None:
            bucket.custo_alocado_total += custo
            bucket.margem_total += float(cte.total) - custo
            bucket.viagens_com_custo_alocado += 1
        else:
            bucket.viagens_pendentes += 1

    return sorted(por_terceiro.values(), key=lambda t: t.receita_total, reverse=True)
