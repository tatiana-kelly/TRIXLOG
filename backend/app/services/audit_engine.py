"""Motor de composição/auditoria por KPI — responde "de onde veio este número?" para as
linhas principais da DRE, com granularidade de registro (arquivo, documento, CT-e, campo,
valor, regra). Nunca recalcula com uma fórmula "independente" fictícia — decompõe a MESMA
fórmula real em suas parcelas de origem, o que é o que realmente prova um número: mostrar os
lançamentos que o formam, não fingir uma segunda fonte de verdade que não existe.

`reconciliar_dre()` soma essas mesmas parcelas por um caminho de código DIFERENTE do
dre_engine.py e compara com o valor oficial — isso é uma checagem real de duas fontes
independentes (já pegou um bug de verdade antes: DRE ignorando custo confirmado via Camada 2).

Ver docs/COST_ALLOCATION.md#10a e #11 (achado real: R$ 292.249,98 de frete terceiro em julho/2026
se decompõe em 35 links diretos + 13 rateados de Carta Frete + 4 via Contrato/Contas a Pagar —
nenhuma dupla contagem, cada CT-e tem no máximo uma fonte de custo)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.carta_frete import CartaFrete
from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.dre_engine import calcular_dre
from app.services.formatting import brl


@dataclass
class LinhaComposicao:
    origem: str  # nome do relatório/tabela de origem
    documento: str | None
    cte_numero: str | None
    campo: str
    valor: float
    regra: str
    arquivo_origem: str | None = None


def _ctes_filtrados(db: Session, mes_referencia: str | None, unidade: str | None) -> list[CTe]:
    query = db.query(CTe)
    if unidade:
        query = query.filter(CTe.unidade == unidade)
    ctes = query.all()
    if mes_referencia:
        ctes = [c for c in ctes if c.data_emissao and c.data_emissao.strftime("%Y-%m") == mes_referencia]
    return ctes


def composicao_receita(db: Session, mes_referencia: str | None = None, unidade: str | None = None) -> list[LinhaComposicao]:
    ctes = _ctes_filtrados(db, mes_referencia, unidade)
    return [
        LinhaComposicao(
            origem="CT-e",
            documento=c.cte_numero,
            cte_numero=c.cte_numero,
            campo="Total",
            valor=float(c.total),
            regra="Receita = CTe.Total, somado direto, sem rateio nem estimativa",
            arquivo_origem=c.arquivo_origem,
        )
        for c in ctes
    ]


def composicao_frete_terceiro(
    db: Session, mes_referencia: str | None = None, unidade: str | None = None
) -> list[LinhaComposicao]:
    ctes = _ctes_filtrados(db, mes_referencia, unidade)
    cte_ids = {c.id for c in ctes}
    ctes_por_id = {c.id: c for c in ctes}

    cartas_por_id = {c.id: c for c in db.query(CartaFrete).all()}
    contratos_por_chave = {(c.contrato_numero, c.unidade): c for c in db.query(ContratoTransporte).all()}

    linhas: list[LinhaComposicao] = []
    for link in db.query(ViagemLink).filter(ViagemLink.status == "resolvido").all():
        if link.cte_id not in cte_ids:
            continue
        cte = ctes_por_id[link.cte_id]

        if link.custo_direto is not None and link.carta_frete_id:
            carta = cartas_por_id.get(link.carta_frete_id)
            if link.metodo_vinculo == "carta_frete_rateado":
                regra = f"Rateio proporcional à receita — Carta Frete {carta.numero if carta else '?'} cobre mais de um CT-e, custo dividido por participação de receita"
            else:
                regra = f"Link direto 1:1 — CTRC {carta.ctrc if carta else '?'} = CTe.cte_numero, mesma unidade"
            linhas.append(
                LinhaComposicao(
                    origem="Carta Frete",
                    documento=carta.numero if carta else None,
                    cte_numero=cte.cte_numero,
                    campo="Frete do Motorista + Pedágio (Despesa)",
                    valor=float(link.custo_direto),
                    regra=regra,
                    arquivo_origem=carta.arquivo_origem if carta else None,
                )
            )
        elif link.contrato_transporte_numero:
            contrato = contratos_por_chave.get((link.contrato_transporte_numero, cte.unidade))
            if contrato:
                linhas.append(
                    LinhaComposicao(
                        origem="Contas a Pagar (via Contrato de Transporte)",
                        documento=contrato.contrato_numero,
                        cte_numero=cte.cte_numero,
                        campo="Adiantamento + Saldo (valor_total_contrato — não soma etapas duas vezes)",
                        valor=float(contrato.valor_total_contrato),
                        regra="Vínculo por heurística nome+data (Camada 2) — sem Carta Frete correspondente para este CT-e",
                        arquivo_origem=None,
                    )
                )
    return linhas


def composicao_categoria_pagamento(
    db: Session, categoria_matcher, mes_referencia: str | None = None, unidade: str | None = None
) -> list[LinhaComposicao]:
    query = db.query(PagamentoFornecedor)
    if unidade:
        query = query.filter(PagamentoFornecedor.unidade == unidade)
    pagamentos = query.all()
    if mes_referencia:
        pagamentos = [p for p in pagamentos if p.dt_emissao and p.dt_emissao.strftime("%Y-%m") == mes_referencia]

    return [
        LinhaComposicao(
            origem="Contas a Pagar",
            documento=p.numero_documento_original,
            cte_numero=None,
            campo=f"{p.fornecedor_nome or 'fornecedor não identificado'} — {p.centro_custo}",
            valor=float(p.valor),
            regra="Custo agregado real — sem chave de placa/CT-e disponível nos relatórios atuais",
            arquivo_origem=p.arquivo_origem,
        )
        for p in pagamentos
        if p.centro_custo and categoria_matcher(p.centro_custo)
    ]


@dataclass
class ItemReconciliacao:
    indicador: str
    valor_dashboard: float
    valor_recalculado: float
    diferenca: float
    status: str  # conciliado | conciliado_com_rateio | parcial | divergente | nao_auditavel
    nota: str


_TOLERANCIA_ARREDONDAMENTO = 0.05


def reconciliar_dre(db: Session, mes_referencia: str | None = None, unidade: str | None = None) -> list[ItemReconciliacao]:
    """Recalcula cada linha da DRE por um caminho de código independente (soma das composições
    registro-a-registro, não a agregação do dre_engine) e compara. Divergência real (> R$ 0,05,
    não arredondamento) nunca é escondida — vira status "divergente" explicitamente."""
    dre = calcular_dre(db, mes_referencia=mes_referencia, unidade=unidade)

    def _status_diferenca(diferenca: float) -> str:
        return "divergente" if abs(diferenca) > _TOLERANCIA_ARREDONDAMENTO else None

    itens = []

    receita_recalc = sum(l.valor for l in composicao_receita(db, mes_referencia, unidade))
    diff = dre.receita_operacional - receita_recalc
    itens.append(
        ItemReconciliacao(
            "Receita Operacional", dre.receita_operacional, receita_recalc, diff,
            _status_diferenca(diff) or "conciliado",
            "Soma direta de CTe.Total — sem alocação, sem rateio.",
        )
    )

    frete_linhas = composicao_frete_terceiro(db, mes_referencia, unidade)
    frete_recalc = sum(l.valor for l in frete_linhas)
    diff = dre.custo_frete_terceiro_confirmado - frete_recalc
    tem_rateio = any("rateado" in l.regra.lower() or "Rateio" in l.regra for l in frete_linhas)
    status = _status_diferenca(diff) or ("conciliado_com_rateio" if tem_rateio else "conciliado")
    nota = f"{dre.custo_frete_terceiro_pendente_qtd_ctes} CT-e's (R$ {brl(dre.custo_frete_terceiro_pendente_receita)}) sem nenhuma fonte de custo — não entram neste total, não são custo zero."
    itens.append(ItemReconciliacao("Custo direto — Frete terceiro", dre.custo_frete_terceiro_confirmado, frete_recalc, diff, status, nota))

    combustivel_recalc = sum(l.valor for l in composicao_categoria_pagamento(db, lambda cc: "OMBUST" in cc, mes_referencia, unidade))
    diff = dre.combustivel - combustivel_recalc
    status_combustivel = _status_diferenca(diff) or ("parcial" if dre.combustivel_risco_sobreposicao_terceiro else "conciliado")
    nota_combustivel = "Soma real de Contas a Pagar — sem chave de placa (agregado empresa/unidade, ver docs/COST_ALLOCATION.md#10)."
    if dre.combustivel_risco_sobreposicao_terceiro:
        nota_combustivel += (
            f" RISCO NÃO CONCILIADO: R$ {brl(dre.combustivel_risco_sobreposicao_terceiro)} de vale-combustível de terceiro"
            " (Carta Frete, já incluído no custo de frete terceiro) pode se sobrepor a este valor —"
            " sem chave que ligue os dois relatórios, não é possível confirmar nem descartar. Nunca deduzido automaticamente."
        )
    itens.append(
        ItemReconciliacao("Combustível (frota própria)", dre.combustivel, combustivel_recalc, diff, status_combustivel, nota_combustivel)
    )

    manutencao_recalc = sum(l.valor for l in composicao_categoria_pagamento(db, lambda cc: "ANUTEN" in cc, mes_referencia, unidade))
    diff = dre.manutencao - manutencao_recalc
    itens.append(
        ItemReconciliacao(
            "Manutenção (frota própria)", dre.manutencao, manutencao_recalc, diff,
            _status_diferenca(diff) or "conciliado",
            "Soma real de Contas a Pagar — sem chave de placa nem confirmação de que é só das 5 placas próprias.",
        )
    )

    if dre.custo_frete_terceiro_pendente_qtd_ctes:
        itens.append(
            ItemReconciliacao(
                "Custo de frete terceiro — parcela pendente", 0.0, 0.0, 0.0, "nao_auditavel",
                f"{dre.custo_frete_terceiro_pendente_qtd_ctes} CT-e's sem Carta Frete nem contrato correspondente — sem informação suficiente para auditar, fica de fora do Resultado até ser conciliado.",
            )
        )

    return itens
