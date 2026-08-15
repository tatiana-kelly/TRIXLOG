"""Rentabilidade por cliente/viagem — docs/COST_ALLOCATION.md#4.

Regra inegociável: nunca apresentar margem "líquida" quando o custo não foi alocado com
confiança. Uma viagem sem ViagemLink resolvido aparece com custo_alocado=None e
margem="nao_determinavel", nunca com custo=0.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink


@dataclass
class ViagemRentabilidade:
    cte_numero: str
    cliente: str
    receita: float
    custo_alocado: float | None
    margem: float | None
    status_alocacao: str  # resolvido | pendente


@dataclass
class RentabilidadeCliente:
    cliente: str
    receita_total: float = 0.0
    custo_alocado_total: float = 0.0
    margem_total: float = 0.0
    viagens_com_custo_alocado: int = 0
    viagens_pendentes: int = 0
    viagens: list[ViagemRentabilidade] = field(default_factory=list)


def calcular_rentabilidade_por_cliente(db: Session) -> list[RentabilidadeCliente]:
    contratos_by_numero = {c.contrato_numero: c for c in db.query(ContratoTransporte).all()}
    links_by_cte = {link.cte_numero: link for link in db.query(ViagemLink).all()}

    por_cliente: dict[str, RentabilidadeCliente] = {}

    for cte in db.query(CTe).all():
        cliente = cte.pagador_frete_nome
        bucket = por_cliente.setdefault(cliente, RentabilidadeCliente(cliente=cliente))

        link = links_by_cte.get(cte.cte_numero)
        custo_alocado = None
        status_alocacao = "pendente"

        if link and link.status == "resolvido" and link.contrato_transporte_numero:
            contrato = contratos_by_numero.get(link.contrato_transporte_numero)
            if contrato:
                custo_alocado = float(contrato.valor_total_contrato)
                status_alocacao = "resolvido"

        receita = float(cte.total)
        margem = (receita - custo_alocado) if custo_alocado is not None else None

        bucket.viagens.append(
            ViagemRentabilidade(
                cte_numero=cte.cte_numero,
                cliente=cliente,
                receita=receita,
                custo_alocado=custo_alocado,
                margem=margem,
                status_alocacao=status_alocacao,
            )
        )
        bucket.receita_total += receita
        if custo_alocado is not None:
            bucket.custo_alocado_total += custo_alocado
            bucket.margem_total += margem
            bucket.viagens_com_custo_alocado += 1
        else:
            bucket.viagens_pendentes += 1

    return sorted(por_cliente.values(), key=lambda c: c.receita_total, reverse=True)
