from datetime import date

from app.models.carta_frete import CartaFrete
from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.custo_fixo_mensal import CustoFixoMensal
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.dre_engine import calcular_dre


def test_expoe_risco_de_sobreposicao_combustivel_vs_vale_terceiro_sem_deduzir(db_session):
    """Achado real (2026-08-16): Adto. Vale Abastec. da Carta Frete pode se sobrepor com
    Contas a Pagar/COMBUSTÍVEIS -- sem chave que ligue os dois relatórios, a plataforma nunca
    deduz automaticamente (seria inventar), só declara o risco quantificado."""
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz"))
    db_session.add(CartaFrete(numero="1", ctrc="1", unidade="matriz", frete_motorista=5000.0, adto_vale_abastecimento=2000.0))
    db_session.add(PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=10000.0, unidade="matriz"))
    db_session.commit()

    dre = calcular_dre(db_session)

    assert dre.combustivel == 10000.0  # nunca deduzido automaticamente
    assert dre.combustivel_risco_sobreposicao_terceiro == 2000.0  # mas o risco fica exposto


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


def test_custo_fixo_mensal_entra_na_despesa_operacional_so_na_visao_consolidada(db_session):
    """Custo fixo informado diretamente pela Tatiana (aluguel de frota, pessoal de frota etc.) não
    tem chave de unidade -- só entra quando a DRE é vista consolidada (sem filtro matriz/filial).
    Filtrando por unidade, o dado faltante fica declarado via custos_fixos_excluidos_por_filtro_unidade,
    nunca dividido/rateado silenciosamente entre matriz e filial."""
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=100000.0, unidade="matriz", data_emissao=date(2026, 7, 1)))
    db_session.add_all(
        [
            CustoFixoMensal(categoria="aluguel_frota", rotulo="Aluguel de frota", mes_referencia="2026-07", valor=80675.0, fonte="teste"),
            CustoFixoMensal(categoria="pessoal_frota", rotulo="Pessoal de frota (salário + comissão + diária)", mes_referencia="2026-07", valor=41698.0, fonte="teste"),
            CustoFixoMensal(categoria="salarios_administrativos", rotulo="Salários administrativos", mes_referencia="2026-07", valor=28000.0, fonte="teste"),
            CustoFixoMensal(categoria="seguro_carga", rotulo="Seguro de carga", mes_referencia="2026-07", valor=3000.0, fonte="teste"),
            CustoFixoMensal(categoria="outros_custos", rotulo="Outros custos", mes_referencia="2026-07", valor=5000.0, fonte="teste"),
            CustoFixoMensal(categoria="aluguel_frota", rotulo="Aluguel de frota", mes_referencia="2026-06", valor=80675.0, fonte="teste"),  # mês diferente, não deve entrar
        ]
    )
    db_session.commit()

    dre_consolidada = calcular_dre(db_session, mes_referencia="2026-07")
    assert dre_consolidada.despesas_operacionais["Aluguel de frota"] == 80675.0
    assert dre_consolidada.despesas_operacionais["Pessoal de frota (salário + comissão + diária)"] == 41698.0
    assert dre_consolidada.despesas_operacionais["Salários administrativos"] == 28000.0
    assert dre_consolidada.despesas_operacionais["Seguro de carga"] == 3000.0
    assert dre_consolidada.despesas_operacionais["Outros custos"] == 5000.0
    assert dre_consolidada.custos_fixos_excluidos_por_filtro_unidade is False

    dre_por_unidade = calcular_dre(db_session, mes_referencia="2026-07", unidade="matriz")
    assert "Aluguel de frota" not in dre_por_unidade.despesas_operacionais
    assert dre_por_unidade.custos_fixos_excluidos_por_filtro_unidade is True


def test_salarios_administrativos_manual_nao_soma_com_administrativas_mao_de_obra_real(db_session):
    """Confirmado com a Tatiana em 2026-08-16: o valor manual de salários administrativos
    SUBSTITUI a categoria real "ADMINISTRATIVAS - MÃO DE OBRA" de Contas a Pagar (que estava
    incompleta) -- nunca soma os dois, senão duplica o mesmo custo."""
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=10000.0, unidade="matriz", data_emissao=date(2026, 5, 1)))
    db_session.add(PagamentoFornecedor(centro_custo="ADMINISTRATIVAS - MÃO DE OBRA", valor=21817.0, unidade="matriz", dt_emissao=date(2026, 5, 1)))
    db_session.add(CustoFixoMensal(categoria="salarios_administrativos", rotulo="Salários administrativos", mes_referencia="2026-05", valor=28000.0, fonte="teste"))
    db_session.commit()

    dre = calcular_dre(db_session, mes_referencia="2026-05")

    assert dre.despesas_operacionais == {"Salários administrativos": 28000.0}
    assert dre.total_despesas_operacionais == 28000.0


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
