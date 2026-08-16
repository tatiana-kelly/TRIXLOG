from datetime import date

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.dre_engine import calcular_dre


def test_receita_e_sempre_soma_real_de_todos_os_ctes(db_session):
    db_session.add_all(
        [
            CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz"),
            CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=2000.0, unidade="matriz"),
        ]
    )
    db_session.commit()

    dre = calcular_dre(db_session)
    assert dre.receita_operacional == 3000.0


def test_custo_terceiro_so_conta_o_confirmado_resto_fica_como_pendente_informativo(db_session):
    cte_confirmado = CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz")
    cte_pendente = CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=2000.0, unidade="matriz")
    db_session.add_all([cte_confirmado, cte_pendente])
    db_session.flush()
    db_session.add(
        ViagemLink(
            cte_id=cte_confirmado.id,
            cte_numero="1",
            status="resolvido",
            custo_direto=400.0,
            metodo_vinculo="carta_frete_direto",
        )
    )
    db_session.commit()

    dre = calcular_dre(db_session)

    assert dre.custo_frete_terceiro_confirmado == 400.0
    assert dre.custo_frete_terceiro_pendente_receita == 2000.0
    assert dre.custo_frete_terceiro_pendente_qtd_ctes == 1
    # margem so desconta o custo confirmado -- nunca inventa custo pro pendente
    assert dre.margem_contribuicao == 3000.0 - 400.0


def test_custo_confirmado_via_camada2_contrato_tambem_entra_na_dre(db_session):
    """Bug real encontrado: links resolvidos pela Camada 2 (contrato_transporte_numero) usam
    fonte diferente de custo do que os da Camada 0 (custo_direto) -- a DRE tem que somar as
    duas, senão CT-e's resolvidos pela heurística caem incorretamente como "pendente"."""
    cte = CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=5000.0, unidade="matriz")
    db_session.add(cte)
    db_session.add(ContratoTransporte(contrato_numero="70", unidade="matriz", valor_total_contrato=1800.0))
    db_session.flush()
    db_session.add(
        ViagemLink(
            cte_id=cte.id,
            cte_numero="1",
            status="resolvido",
            contrato_transporte_numero="70",
            metodo_vinculo="heuristica_placa_data",
        )
    )
    db_session.commit()

    dre = calcular_dre(db_session)

    assert dre.custo_frete_terceiro_confirmado == 1800.0
    assert dre.custo_frete_terceiro_pendente_qtd_ctes == 0
    assert dre.custo_frete_terceiro_pendente_receita == 0.0


def test_despesas_operacionais_e_financeiras_reais(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=10000.0, unidade="matriz"))
    db_session.add_all(
        [
            PagamentoFornecedor(centro_custo="ADMINISTRATIVAS - GERAL", valor=500.0, unidade="matriz", dt_emissao=date(2026, 5, 1)),
            PagamentoFornecedor(centro_custo="SEGUROS", valor=200.0, unidade="matriz", dt_emissao=date(2026, 5, 1)),
            PagamentoFornecedor(centro_custo="DESPESAS FINANCEIRAS", valor=100.0, unidade="matriz", dt_emissao=date(2026, 5, 1)),
            PagamentoFornecedor(centro_custo="FRETE TERCEIRO", valor=99999.0, unidade="matriz", dt_emissao=date(2026, 5, 1)),
        ]
    )
    db_session.commit()

    dre = calcular_dre(db_session)

    assert dre.despesas_operacionais == {"Administrativas": 500.0, "Seguros": 200.0}
    assert dre.total_despesas_operacionais == 700.0
    assert dre.despesas_financeiras == 100.0
    # FRETE TERCEIRO do Contas a Pagar nunca entra direto na DRE -- so via ViagemLink.custo_direto,
    # pra nao contar duas vezes o mesmo custo (Camada 2 ja soma isso via ContratoTransporte)
    assert dre.margem_contribuicao == 10000.0
    assert dre.resultado_operacional == 10000.0 - 700.0
    assert dre.resultado_gerencial == 10000.0 - 700.0 - 100.0


def test_filtra_por_mes_e_unidade(db_session):
    db_session.add_all(
        [
            CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz", data_emissao=date(2026, 5, 10)),
            CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=5000.0, unidade="matriz", data_emissao=date(2026, 6, 10)),
            CTe(cte_numero="3", cte_serie="1", pagador_frete_nome="C", total=7000.0, unidade="filial", data_emissao=date(2026, 5, 10)),
        ]
    )
    db_session.commit()

    dre_maio_matriz = calcular_dre(db_session, mes_referencia="2026-05", unidade="matriz")
    assert dre_maio_matriz.receita_operacional == 1000.0
