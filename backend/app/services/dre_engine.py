"""DRE Gerencial — docs/COST_ALLOCATION.md#3, PRP da Tatiana seção 26.

Regra inegociável (a mesma de todo o resto da plataforma): nunca apresentar um "Resultado" como
se fosse completo quando parte do custo de frete terceiro ainda não foi confirmada. A receita
total é sempre 100% real (soma direta de CTe.total). O custo direto de frete terceiro só entra
na conta pela parte já CONFIRMADA (ViagemLink resolvido, Camada 0/2) — a parte pendente aparece
como linha informativa separada (receita e quantidade de CT-e's), nunca é tratada como custo
zero nem escondida.

Combustível e manutenção de frota própria entram como custo agregado real (não têm chave por
CT-e ainda — ver docs/COST_ALLOCATION.md#10) e afetam a receita total da empresa, não só a fatia
com custo terceiro confirmado (são custos da operação como um todo, não de uma viagem
específica)."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.custo_lookup import custo_confirmado_por_cte


@dataclass
class LinhaDRE:
    conta: str
    valor: float
    real: bool = True  # False = derivado/calculado (subtotal), True = somado direto do dado


@dataclass
class DRE:
    receita_operacional: float = 0.0
    custo_frete_terceiro_confirmado: float = 0.0
    custo_frete_terceiro_pendente_receita: float = 0.0
    custo_frete_terceiro_pendente_qtd_ctes: int = 0
    combustivel: float = 0.0
    manutencao: float = 0.0
    margem_contribuicao: float = 0.0
    despesas_operacionais: dict[str, float] = field(default_factory=dict)
    total_despesas_operacionais: float = 0.0
    resultado_operacional: float = 0.0
    despesas_financeiras: float = 0.0
    resultado_gerencial: float = 0.0
    pct_receita_com_custo_terceiro_confirmado: float = 0.0


_CATEGORIAS_DESPESA_OPERACIONAL = {
    "ADMINISTRATIVAS - GERAL": "Administrativas",
    "ADMINISTRATIVAS - MÃO DE OBRA": "Mão de obra",
    "LICENÇA DE USO SOFTWARE": "Software",
    "MEDICINA DO TRABALHO": "Medicina do trabalho",
    "SEGUROS": "Seguros",
}


def calcular_dre(db: Session, mes_referencia: str | None = None, unidade: str | None = None) -> DRE:
    dre = DRE()

    ctes_query = db.query(CTe)
    if unidade:
        ctes_query = ctes_query.filter(CTe.unidade == unidade)
    ctes = ctes_query.all()
    if mes_referencia:
        ctes = [c for c in ctes if c.data_emissao and c.data_emissao.strftime("%Y-%m") == mes_referencia]

    dre.receita_operacional = sum(float(c.total) for c in ctes)

    links_resolvidos = custo_confirmado_por_cte(db, ctes)
    dre.custo_frete_terceiro_confirmado = sum(links_resolvidos.values())

    ctes_pendentes = [c for c in ctes if c.id not in links_resolvidos]
    dre.custo_frete_terceiro_pendente_receita = sum(float(c.total) for c in ctes_pendentes)
    dre.custo_frete_terceiro_pendente_qtd_ctes = len(ctes_pendentes)
    dre.pct_receita_com_custo_terceiro_confirmado = (
        round((dre.receita_operacional - dre.custo_frete_terceiro_pendente_receita) / dre.receita_operacional * 100, 1)
        if dre.receita_operacional
        else 0.0
    )

    pagamentos_query = db.query(PagamentoFornecedor)
    if unidade:
        pagamentos_query = pagamentos_query.filter(PagamentoFornecedor.unidade == unidade)
    pagamentos = pagamentos_query.all()
    if mes_referencia:
        pagamentos = [p for p in pagamentos if p.dt_emissao and p.dt_emissao.strftime("%Y-%m") == mes_referencia]

    def _soma_categoria(matcher) -> float:
        return sum(float(p.valor) for p in pagamentos if p.centro_custo and matcher(p.centro_custo))

    dre.combustivel = _soma_categoria(lambda cc: "OMBUST" in cc)
    dre.manutencao = _soma_categoria(lambda cc: "ANUTEN" in cc)

    dre.margem_contribuicao = dre.receita_operacional - dre.custo_frete_terceiro_confirmado - dre.combustivel - dre.manutencao

    for centro_custo_real, rotulo in _CATEGORIAS_DESPESA_OPERACIONAL.items():
        valor = sum(float(p.valor) for p in pagamentos if p.centro_custo == centro_custo_real)
        if valor:
            dre.despesas_operacionais[rotulo] = valor
    dre.total_despesas_operacionais = sum(dre.despesas_operacionais.values())

    dre.resultado_operacional = dre.margem_contribuicao - dre.total_despesas_operacionais

    dre.despesas_financeiras = _soma_categoria(lambda cc: cc == "DESPESAS FINANCEIRAS")
    dre.resultado_gerencial = dre.resultado_operacional - dre.despesas_financeiras

    return dre
