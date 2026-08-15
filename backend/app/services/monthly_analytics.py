"""Análises mensais — filtros mensais, comparativo mês a mês, rentabilidade por cliente mês a
mês e detecção de desvios. Consome `rentabilidade_engine`, nunca recalcula alocação de custo por
conta própria (mesma regra: nunca margem "líquida" sem custo alocado).

Este módulo só detecta e quantifica (FATO/CÁLCULO) — não atribui causa. Causa provável é
trabalho do Investigador (ver .claude/agents/investigador.md), não deste motor determinístico.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente


def listar_meses_disponiveis(db: Session) -> list[str]:
    """Meses (YYYY-MM) com pelo menos 1 CT-e importado — para o seletor de filtro mensal."""
    meses = {cte.data_emissao.strftime("%Y-%m") for cte in db.query(CTe).all() if cte.data_emissao}
    return sorted(meses)


@dataclass
class ClienteMesRentabilidade:
    cliente: str
    receita_total: float = 0.0
    custo_alocado_total: float = 0.0
    margem_total: float = 0.0
    viagens_com_custo_alocado: int = 0
    viagens_pendentes: int = 0
    pct_custo_nao_alocado: float = 0.0  # % das viagens do mês ainda sem custo confirmado


def rentabilidade_mensal_por_cliente(db: Session, mes_referencia: str, unidade: str | None = None) -> list[ClienteMesRentabilidade]:
    clientes = calcular_rentabilidade_por_cliente(db, mes_referencia=mes_referencia, unidade=unidade)
    out = []
    for c in clientes:
        total_viagens = c.viagens_com_custo_alocado + c.viagens_pendentes
        pct_pendente = (c.viagens_pendentes / total_viagens * 100) if total_viagens else 0.0
        out.append(
            ClienteMesRentabilidade(
                cliente=c.cliente,
                receita_total=c.receita_total,
                custo_alocado_total=c.custo_alocado_total,
                margem_total=c.margem_total,
                viagens_com_custo_alocado=c.viagens_com_custo_alocado,
                viagens_pendentes=c.viagens_pendentes,
                pct_custo_nao_alocado=round(pct_pendente, 1),
            )
        )
    return out


@dataclass
class ComparativoMensalCliente:
    cliente: str
    por_mes: dict[str, ClienteMesRentabilidade] = field(default_factory=dict)


def comparativo_mensal(db: Session, meses: list[str], unidade: str | None = None) -> list[ComparativoMensalCliente]:
    """Uma linha por cliente, uma coluna por mês — para a tela de comparativo mês a mês."""
    por_cliente: dict[str, ComparativoMensalCliente] = {}
    for mes in meses:
        for item in rentabilidade_mensal_por_cliente(db, mes, unidade=unidade):
            bucket = por_cliente.setdefault(item.cliente, ComparativoMensalCliente(cliente=item.cliente))
            bucket.por_mes[mes] = item
    return sorted(por_cliente.values(), key=lambda c: c.cliente)


@dataclass
class Desvio:
    cliente: str
    mes_atual: str
    mes_anterior: str
    receita_atual: float
    receita_anterior: float
    variacao_absoluta: float
    variacao_percentual: float
    tipo: str  # "queda_receita" | "aumento_receita"


def detectar_desvios_mensais(
    db: Session,
    mes_atual: str,
    mes_anterior: str,
    unidade: str | None = None,
    limiar_percentual: float = 20.0,
    limiar_absoluto: float = 1000.0,
) -> list[Desvio]:
    """Compara receita por cliente entre dois meses e sinaliza variação material — precisa passar
    os dois limiares (percentual E absoluto, docs/COST_ALLOCATION.md / .claude/rules) para não
    sinalizar ruído em cliente pequeno com variação percentual grande mas irrelevante em R$."""
    atual = {c.cliente: c.receita_total for c in rentabilidade_mensal_por_cliente(db, mes_atual, unidade=unidade)}
    anterior = {c.cliente: c.receita_total for c in rentabilidade_mensal_por_cliente(db, mes_anterior, unidade=unidade)}

    desvios = []
    for cliente in set(atual) | set(anterior):
        receita_atual = atual.get(cliente, 0.0)
        receita_anterior = anterior.get(cliente, 0.0)
        variacao_absoluta = receita_atual - receita_anterior
        variacao_percentual = (variacao_absoluta / receita_anterior * 100) if receita_anterior else (100.0 if receita_atual else 0.0)

        if abs(variacao_absoluta) < limiar_absoluto or abs(variacao_percentual) < limiar_percentual:
            continue

        desvios.append(
            Desvio(
                cliente=cliente,
                mes_atual=mes_atual,
                mes_anterior=mes_anterior,
                receita_atual=receita_atual,
                receita_anterior=receita_anterior,
                variacao_absoluta=variacao_absoluta,
                variacao_percentual=round(variacao_percentual, 1),
                tipo="queda_receita" if variacao_absoluta < 0 else "aumento_receita",
            )
        )

    return sorted(desvios, key=lambda d: abs(d.variacao_absoluta), reverse=True)
