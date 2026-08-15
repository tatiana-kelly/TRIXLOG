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
from app.services.client_identity import build_canonical_names


@dataclass
class ViagemRentabilidade:
    cte_numero: str
    cliente: str
    unidade: str | None
    mes_referencia: str | None  # "YYYY-MM", derivado de CTe.data_emissao
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


def _mes_referencia(cte: CTe) -> str | None:
    return cte.data_emissao.strftime("%Y-%m") if cte.data_emissao else None


def calcular_rentabilidade_por_cliente(
    db: Session, mes_referencia: str | None = None, unidade: str | None = None
) -> list[RentabilidadeCliente]:
    """mes_referencia: filtra por "YYYY-MM" (baseado em CTe.data_emissao). unidade: filtra por
    "matriz"|"filial". Sem filtros, agrega tudo que foi importado até agora."""
    # chave (numero, unidade) — matriz e filial reutilizam a mesma faixa de numeração de contrato.
    contratos_by_key = {(c.contrato_numero, c.unidade): c for c in db.query(ContratoTransporte).all()}
    links_by_cte_id = {link.cte_id: link for link in db.query(ViagemLink).all()}

    # Nome canônico calculado sobre TODOS os CT-e's do banco (não só os filtrados por mês/unidade)
    # para o mesmo cliente sempre resolver para o mesmo nome de exibição, independente do filtro
    # aplicado na tela. Ver docs/COST_ALLOCATION.md#8b — mescla só grafia (MINERVA S A / S.A.),
    # nunca empresas distintas com nome parecido (CHINT matriz China x CHINT Brasil continuam
    # separadas).
    todos_nomes = [nome for (nome,) in db.query(CTe.pagador_frete_nome).all()]
    nome_canonico = build_canonical_names(todos_nomes)

    por_cliente: dict[str, RentabilidadeCliente] = {}

    query = db.query(CTe)
    if unidade:
        query = query.filter(CTe.unidade == unidade)

    for cte in query.all():
        cte_mes = _mes_referencia(cte)
        if mes_referencia and cte_mes != mes_referencia:
            continue

        cliente = nome_canonico[cte.pagador_frete_nome]
        bucket = por_cliente.setdefault(cliente, RentabilidadeCliente(cliente=cliente))

        link = links_by_cte_id.get(cte.id)
        custo_alocado = None
        status_alocacao = "pendente"

        if link and link.status == "resolvido" and link.contrato_transporte_numero:
            contrato = contratos_by_key.get((link.contrato_transporte_numero, cte.unidade))
            if contrato:
                custo_alocado = float(contrato.valor_total_contrato)
                status_alocacao = "resolvido"

        receita = float(cte.total)
        margem = (receita - custo_alocado) if custo_alocado is not None else None

        bucket.viagens.append(
            ViagemRentabilidade(
                cte_numero=cte.cte_numero,
                cliente=cliente,
                unidade=cte.unidade,
                mes_referencia=cte_mes,
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
