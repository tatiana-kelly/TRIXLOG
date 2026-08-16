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

from app.models.carta_frete import CartaFrete
from app.models.cte import CTe
from app.models.custo_fixo_mensal import CustoFixoMensal
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
    combustivel_risco_sobreposicao_terceiro: float = 0.0
    manutencao: float = 0.0
    margem_contribuicao: float = 0.0
    despesas_operacionais: dict[str, float] = field(default_factory=dict)
    total_despesas_operacionais: float = 0.0
    resultado_operacional: float = 0.0
    despesas_financeiras: float = 0.0
    resultado_gerencial: float = 0.0
    pct_receita_com_custo_terceiro_confirmado: float = 0.0
    custos_fixos_excluidos_por_filtro_unidade: bool = False


# "ADMINISTRATIVAS - MÃO DE OBRA" NÃO entra mais aqui — confirmado com a Tatiana em 2026-08-16
# que a categoria real de Contas a Pagar estava incompleta (zero lançamentos em julho/2026) e
# foi substituída pelo valor real e completo da folha administrativa, informado diretamente
# (CustoFixoMensal, categoria "salarios_administrativos") — ver calcular_dre() abaixo.
_CATEGORIAS_DESPESA_OPERACIONAL = {
    "ADMINISTRATIVAS - GERAL": "Administrativas",
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

    # Risco de sobreposição — achado real confirmado com a Tatiana (2026-08-16): a Carta Frete
    # tem um campo "Adto. Vale Abastec." (parte do Frete do Motorista liquidada como vale-
    # combustível ao terceiro). Se a TRIXLOG paga o posto direto pra cobrir esse vale, o mesmo
    # evento pode aparecer TAMBÉM em Contas a Pagar como "COMBUSTÍVEIS" — dupla contagem em
    # potencial (uma vez dentro do custo_frete_terceiro_confirmado via Frete do Motorista bruto,
    # outra vez aqui). Sem chave que ligue os dois relatórios (Contas a Pagar de combustível não
    # referencia motorista/CTRC/carta-frete), NÃO dá pra confirmar nem descartar — só declarar.
    # Nunca subtraído automaticamente: seria inventar uma dedução sem prova.
    cartas_query = db.query(CartaFrete)
    if unidade:
        cartas_query = cartas_query.filter(CartaFrete.unidade == unidade)
    cartas = cartas_query.all()
    if mes_referencia:
        cartas = [c for c in cartas if c.data_emissao and c.data_emissao.strftime("%Y-%m") == mes_referencia]
    dre.combustivel_risco_sobreposicao_terceiro = sum(float(c.adto_vale_abastecimento) for c in cartas)

    dre.margem_contribuicao = dre.receita_operacional - dre.custo_frete_terceiro_confirmado - dre.combustivel - dre.manutencao

    for centro_custo_real, rotulo in _CATEGORIAS_DESPESA_OPERACIONAL.items():
        valor = sum(float(p.valor) for p in pagamentos if p.centro_custo == centro_custo_real)
        if valor:
            dre.despesas_operacionais[rotulo] = valor

    # Custos fixos mensais informados diretamente pela Tatiana (aluguel de frota, pessoal de
    # frota, salários administrativos, seguro de carga, outros) — nunca aparecem em nenhum
    # relatório importado, e não têm chave de unidade (valor consolidado da empresa). Só entram
    # na visão consolidada (sem filtro de unidade) — numa visão por matriz/filial isolada não há
    # como ratear sem inventar uma proporção, então ficam de fora e o dado faltante é declarado.
    dre.custos_fixos_excluidos_por_filtro_unidade = bool(unidade)
    if not unidade:
        custos_fixos_query = db.query(CustoFixoMensal)
        if mes_referencia:
            custos_fixos_query = custos_fixos_query.filter(CustoFixoMensal.mes_referencia == mes_referencia)
        for cf in custos_fixos_query.all():
            dre.despesas_operacionais[cf.rotulo] = dre.despesas_operacionais.get(cf.rotulo, 0.0) + float(cf.valor)

    dre.total_despesas_operacionais = sum(dre.despesas_operacionais.values())

    dre.resultado_operacional = dre.margem_contribuicao - dre.total_despesas_operacionais

    dre.despesas_financeiras = _soma_categoria(lambda cc: cc == "DESPESAS FINANCEIRAS")
    dre.resultado_gerencial = dre.resultado_operacional - dre.despesas_financeiras

    return dre
