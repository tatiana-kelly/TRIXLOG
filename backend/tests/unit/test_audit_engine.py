from datetime import date

from app.models.carta_frete import CartaFrete
from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.audit_engine import (
    composicao_categoria_pagamento,
    composicao_frete_terceiro,
    composicao_receita,
    reconciliar_dre,
)


def test_composicao_receita_lista_cada_cte(db_session):
    db_session.add_all(
        [
            CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz", arquivo_origem="cte_matriz_maio.xlsx"),
            CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=2000.0, unidade="matriz", arquivo_origem="cte_matriz_maio.xlsx"),
        ]
    )
    db_session.commit()

    linhas = composicao_receita(db_session)
    assert len(linhas) == 2
    assert sum(l.valor for l in linhas) == 3000.0
    assert all(l.origem == "CT-e" for l in linhas)


def test_composicao_frete_terceiro_soma_bate_com_dre_e_nunca_duplica(db_session):
    """Mesmo caso real auditado: um CT-e via Carta Frete direta, outro via Contas a Pagar
    (sem Carta Frete) -- a soma da composição tem que bater exatamente com o total da DRE, e
    cada CT-e aparece no máximo uma vez (nunca as duas fontes juntas)."""
    cte_carta = CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=5000.0, unidade="matriz")
    cte_contrato = CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=3000.0, unidade="matriz")
    db_session.add_all([cte_carta, cte_contrato])
    db_session.add(CartaFrete(numero="53", ctrc="1", unidade="matriz", frete_motorista=4000.0))
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=1800.0))
    db_session.flush()
    db_session.add(
        ViagemLink(
            cte_id=cte_carta.id,
            cte_numero="1",
            status="resolvido",
            custo_direto=4000.0,
            carta_frete_id=db_session.query(CartaFrete).first().id,
            metodo_vinculo="carta_frete_direto",
        )
    )
    db_session.add(
        ViagemLink(cte_id=cte_contrato.id, cte_numero="2", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual")
    )
    db_session.commit()

    linhas = composicao_frete_terceiro(db_session)
    assert len(linhas) == 2
    ctes_vistos = [l.cte_numero for l in linhas]
    assert len(ctes_vistos) == len(set(ctes_vistos))  # nunca o mesmo CT-e duas vezes
    assert sum(l.valor for l in linhas) == 5800.0

    origem_carta = next(l for l in linhas if l.cte_numero == "1")
    assert origem_carta.origem == "Carta Frete"
    origem_contrato = next(l for l in linhas if l.cte_numero == "2")
    assert origem_contrato.origem == "Contas a Pagar (via Contrato de Transporte)"


def test_composicao_categoria_pagamento_filtra_por_centro_custo(db_session):
    db_session.add_all(
        [
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=500.0, unidade="matriz", fornecedor_nome="POSTO X", dt_emissao=date(2026, 5, 1)),
            PagamentoFornecedor(centro_custo="FRETE TERCEIRO", valor=9999.0, unidade="matriz", dt_emissao=date(2026, 5, 1)),
        ]
    )
    db_session.commit()

    linhas = composicao_categoria_pagamento(db_session, lambda cc: "OMBUST" in cc)
    assert len(linhas) == 1
    assert linhas[0].valor == 500.0
    assert "POSTO X" in linhas[0].campo


def test_reconciliacao_bate_quando_tudo_confere(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=5000.0, unidade="matriz"))
    db_session.commit()

    itens = reconciliar_dre(db_session)
    receita = next(i for i in itens if i.indicador == "Receita Operacional")
    assert receita.valor_dashboard == receita.valor_recalculado == 5000.0
    assert receita.diferenca == 0.0
    assert receita.status == "conciliado"


def test_reconciliacao_marca_rateio_quando_presente(db_session):
    cte_a = CTe(cte_numero="371", cte_serie="1", pagador_frete_nome="X", unidade="matriz", total=3000.0)
    cte_b = CTe(cte_numero="374", cte_serie="1", pagador_frete_nome="Y", unidade="matriz", total=1000.0)
    db_session.add_all([cte_a, cte_b])
    db_session.add(CartaFrete(numero="69", ctrc="371,374", unidade="matriz", frete_motorista=4000.0))
    db_session.flush()
    from app.services.cost_allocation.camada0_carta_frete import run_camada0

    run_camada0(db_session)

    itens = reconciliar_dre(db_session)
    frete = next(i for i in itens if i.indicador == "Custo direto — Frete terceiro")
    assert frete.status == "conciliado_com_rateio"
    assert frete.diferenca == 0.0


def test_reconciliacao_sinaliza_parcela_pendente_como_nao_auditavel(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=5000.0, unidade="matriz"))
    db_session.commit()

    itens = reconciliar_dre(db_session)
    pendente = next((i for i in itens if "pendente" in i.indicador.lower()), None)
    assert pendente is not None
    assert pendente.status == "nao_auditavel"
