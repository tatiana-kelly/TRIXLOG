"""Central de Decisões — aplica .claude/rules/alert-contract.md e diagnostic-quality.md a dado
real já calculado pela plataforma (rentabilidade_engine, monthly_analytics). Não chama LLM, não
infere causa como fato — toda "causa provável" aqui é rotulada como hipótese a validar, nunca
como diagnóstico fechado (ver .claude/rules/diagnostic-quality.md: "nunca tratar correlação
como causalidade comprovada"). Responsabilidade de investigar a fundo é do Investigador
(.claude/agents/investigador.md), não deste motor determinístico.

Cada decisão carrega os campos exigidos pelo contrato de alertas: o que desviou, quanto
representa, onde está concentrado, hipóteses de causa (com confiança), dado faltante relevante,
consequência de não agir, três ações possíveis, ação recomendada, dono (por papel, nunca pessoa
específica — este motor não tem como saber quem é o responsável real), e KPI de validação."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.monthly_analytics import detectar_desvios_mensais, listar_meses_disponiveis
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente


def _brl(valor: float) -> str:
    """Formato brasileiro (R$ 1.234,56) — Python's {:,.2f} sozinho é formato americano
    (1,234.56), inconsistente com o resto da plataforma (toLocaleString('pt-BR') no frontend)."""
    inteiro, decimal = f"{valor:,.2f}".split(".")
    return inteiro.replace(",", ".") + "," + decimal


@dataclass
class Decisao:
    tipo: str  # cliente_deficitario | desvio_receita | cobertura_baixa
    severidade: str  # critico | atencao | informacao
    situacao: str
    evidencia: str
    impacto_reais: float
    onde: str
    hipoteses_causa: list[str]
    confianca: str  # baixa | media | alta
    dado_faltante: str
    consequencia: str
    acoes_possiveis: list[str]
    acao_recomendada: str
    dono_papel: str
    kpi_validacao: str


def _decisoes_clientes_deficitarios(db: Session, unidade: str | None) -> list[Decisao]:
    clientes = calcular_rentabilidade_por_cliente(db, unidade=unidade)
    decisoes = []
    for c in clientes:
        # só considera cliente deficitário se a margem negativa é CONFIRMADA — pelo menos 1
        # viagem com custo alocado e o total ainda assim é negativo. Nunca usa "não determinável"
        # como se fosse prejuízo.
        if c.viagens_com_custo_alocado == 0 or c.margem_total >= 0:
            continue

        pct_pendente = round(c.viagens_pendentes / (c.viagens_com_custo_alocado + c.viagens_pendentes) * 100, 1)
        severidade = "critico" if c.margem_total < -10000 else "atencao"

        decisoes.append(
            Decisao(
                tipo="cliente_deficitario",
                severidade=severidade,
                situacao=f"Margem confirmada negativa em {c.cliente}",
                evidencia=f"{c.viagens_com_custo_alocado} viagens com custo alocado, receita R$ {_brl(c.receita_total)}, custo R$ {_brl(c.custo_alocado_total)}",
                impacto_reais=abs(c.margem_total),
                onde=c.cliente,
                hipoteses_causa=[
                    "Tabela comercial abaixo do custo real de operação para este cliente/rota (hipótese, não confirmada)",
                    "Concentração em rota ou modal de custo estruturalmente mais alto (hipótese, não confirmada)",
                    f"Ainda há {pct_pendente}% das viagens deste cliente sem custo alocado — a margem real pode ser diferente quando isso for resolvido",
                ],
                confianca="media" if pct_pendente < 30 else "baixa",
                dado_faltante=f"{c.viagens_pendentes} viagens deste cliente sem custo de frete confirmado" if c.viagens_pendentes else "nenhum — margem calculada sobre 100% das viagens do cliente",
                consequencia=f"Continuar operando este cliente nas condições atuais mantém uma perda confirmada de R$ {_brl(abs(c.margem_total))} nas viagens já resolvidas",
                acoes_possiveis=[
                    "Revisar tabela comercial/frete deste cliente",
                    "Avaliar se a rota/modal predominante deste cliente é estruturalmente deficitária",
                    "Priorizar a conciliação das viagens pendentes deste cliente antes de qualquer decisão comercial",
                ],
                acao_recomendada="Priorizar a conciliação das viagens pendentes deste cliente antes de qualquer decisão comercial" if pct_pendente >= 30 else "Revisar tabela comercial/frete deste cliente",
                dono_papel="Comercial / Diretoria",
                kpi_validacao="Margem confirmada do cliente deixa de ser negativa, ou % de viagens pendentes cai abaixo de 20%",
            )
        )
    return decisoes


def _decisoes_desvios_recentes(db: Session, unidade: str | None) -> list[Decisao]:
    meses = listar_meses_disponiveis(db)
    if len(meses) < 2:
        return []
    mes_atual, mes_anterior = meses[-1], meses[-2]
    desvios = detectar_desvios_mensais(db, mes_atual=mes_atual, mes_anterior=mes_anterior, unidade=unidade)

    decisoes = []
    for d in desvios[:10]:  # maior impacto absoluto primeiro (já ordenado por detectar_desvios_mensais)
        tipo_label = "queda" if d.tipo == "queda_receita" else "aumento"
        decisoes.append(
            Decisao(
                tipo="desvio_receita",
                severidade="critico" if d.tipo == "queda_receita" and abs(d.variacao_absoluta) > 20000 else "atencao",
                situacao=f"{tipo_label.capitalize()} de receita em {d.cliente} ({mes_anterior} → {mes_atual})",
                evidencia=f"R$ {_brl(d.receita_anterior)} → R$ {_brl(d.receita_atual)} ({d.variacao_percentual:+.1f}%)",
                impacto_reais=abs(d.variacao_absoluta),
                onde=d.cliente,
                hipoteses_causa=[
                    "Sazonalidade do cliente (hipótese, não confirmada — precisa comparar com mesmo mês do ano anterior quando houver histórico)",
                    "Perda ou ganho de contrato/rota específica com este cliente (hipótese, não confirmada)",
                    "Relatório do mês pode estar parcialmente importado — confirmar cobertura antes de agir",
                ],
                confianca="baixa",
                dado_faltante="Causa real não investigada — este é um alerta de detecção (FATO/CÁLCULO), não de diagnóstico",
                consequencia=f"Se a queda for estrutural (não sazonal), representa R$ {_brl(abs(d.variacao_absoluta))}/mês de receita em risco" if d.tipo == "queda_receita" else "Aumento pode indicar oportunidade de reforçar o relacionamento comercial",
                acoes_possiveis=[
                    "Confirmar com o comercial se há motivo conhecido (contrato, sazonalidade, incidente)",
                    "Cruzar com histórico do mesmo mês em anos anteriores, quando disponível",
                    "Acompanhar o próximo mês antes de qualquer ação — 1 ponto de dado não confirma tendência",
                ],
                acao_recomendada="Confirmar com o comercial se há motivo conhecido antes de qualquer ação",
                dono_papel="Comercial",
                kpi_validacao=f"Receita de {d.cliente} no próximo mês — confirma se é pontual ou estrutural",
            )
        )
    return decisoes


def listar_decisoes(db: Session, unidade: str | None = None) -> list[Decisao]:
    decisoes = _decisoes_clientes_deficitarios(db, unidade) + _decisoes_desvios_recentes(db, unidade)
    ordem_severidade = {"critico": 0, "atencao": 1, "informacao": 2}
    return sorted(decisoes, key=lambda d: (ordem_severidade[d.severidade], -d.impacto_reais))
