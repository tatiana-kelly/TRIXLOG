"""Rentabilidade por rota (origem → destino) — PRP da Tatiana seção 24. Chave = CTe.local_coleta
+ CTe.local_entrega, exatamente como vêm no relatório real (nenhuma normalização de cidade
inventada). Mesma regra de custo confirmado do resto da plataforma — ver custo_lookup.py."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.services.custo_lookup import custo_confirmado_por_cte


@dataclass
class RentabilidadeRota:
    origem: str
    destino: str
    qtd_ctes: int = 0
    receita_total: float = 0.0
    custo_alocado_total: float = 0.0
    margem_total: float = 0.0
    viagens_com_custo_alocado: int = 0
    viagens_pendentes: int = 0


def calcular_rentabilidade_por_rota(
    db: Session, mes_referencia: str | None = None, unidade: str | None = None
) -> list[RentabilidadeRota]:
    query = db.query(CTe)
    if unidade:
        query = query.filter(CTe.unidade == unidade)
    ctes = query.all()
    if mes_referencia:
        ctes = [c for c in ctes if c.data_emissao and c.data_emissao.strftime("%Y-%m") == mes_referencia]

    ctes_com_rota = [c for c in ctes if c.local_coleta and c.local_entrega]
    custo_por_cte = custo_confirmado_por_cte(db, ctes_com_rota)

    por_rota: dict[tuple[str, str], RentabilidadeRota] = {}
    for cte in ctes_com_rota:
        chave = (cte.local_coleta, cte.local_entrega)
        bucket = por_rota.setdefault(chave, RentabilidadeRota(origem=cte.local_coleta, destino=cte.local_entrega))

        bucket.qtd_ctes += 1
        bucket.receita_total += float(cte.total)
        custo = custo_por_cte.get(cte.id)
        if custo is not None:
            bucket.custo_alocado_total += custo
            bucket.margem_total += float(cte.total) - custo
            bucket.viagens_com_custo_alocado += 1
        else:
            bucket.viagens_pendentes += 1

    return sorted(por_rota.values(), key=lambda r: r.receita_total, reverse=True)
