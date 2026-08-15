"""Teste 3 de docs/ACCEPTANCE_TESTS.md — Camada 2 nunca decide automaticamente com 2+ candidatos."""

from datetime import date

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.cost_allocation.heuristic_link import run_camada2


def test_um_candidato_unico_vincula_automaticamente(db_session):
    db_session.add(
        CTe(
            cte_numero="1",
            cte_serie="1",
            pagador_frete_nome="CLIENTE X",
            proprietario_veiculo_nome="TRANSPORTADORA UNICA",
            total=1000.0,
            data_emissao=date(2026, 7, 10),
        )
    )
    db_session.add(ContratoTransporte(contrato_numero="50", fornecedor_nome="TRANSPORTADORA UNICA", valor_total_contrato=600.0))
    db_session.add(
        PagamentoFornecedor(
            fornecedor_nome="TRANSPORTADORA UNICA",
            valor=600.0,
            tipo_documento="contrato_transporte",
            numero_documento="50",
            tipo_parcela="saldo",
            dt_emissao=date(2026, 7, 11),
        )
    )
    db_session.commit()

    stats = run_camada2(db_session)
    assert stats["auto_linked"] == 1
    assert stats["ambiguous"] == 0


def test_dois_candidatos_ambiguos_nunca_vincula_automaticamente(db_session):
    """Espelha o caso real de examples/reconciliation_gap_case.md: 2 transportadores na mesma
    janela de data — a Camada 2 deve recusar decidir sozinha."""
    db_session.add(
        CTe(
            cte_numero="412",
            cte_serie="1",
            pagador_frete_nome="AGROVALE INDÚSTRIA LTDA",
            proprietario_veiculo_nome="TRANSPORTADORA AMBIGUA",
            total=7200.0,
            data_emissao=date(2026, 7, 15),
        )
    )
    db_session.add(ContratoTransporte(contrato_numero="94", fornecedor_nome="TRANSPORTADORA AMBIGUA", valor_total_contrato=5000.0))
    db_session.add(ContratoTransporte(contrato_numero="97", fornecedor_nome="TRANSPORTADORA AMBIGUA", valor_total_contrato=5200.0))
    db_session.add(
        PagamentoFornecedor(
            fornecedor_nome="TRANSPORTADORA AMBIGUA",
            valor=5000.0,
            tipo_documento="contrato_transporte",
            numero_documento="94",
            tipo_parcela="saldo",
            dt_emissao=date(2026, 7, 16),
        )
    )
    db_session.add(
        PagamentoFornecedor(
            fornecedor_nome="TRANSPORTADORA AMBIGUA",
            valor=5200.0,
            tipo_documento="contrato_transporte",
            numero_documento="97",
            tipo_parcela="saldo",
            dt_emissao=date(2026, 7, 17),
        )
    )
    db_session.commit()

    stats = run_camada2(db_session)
    assert stats["auto_linked"] == 0
    assert stats["ambiguous"] == 1

    from app.models.viagem_link import ViagemLink

    link = db_session.query(ViagemLink).filter(ViagemLink.cte_numero == "412").one()
    assert link.status == "pendente"
    assert link.contrato_transporte_numero is None
    assert set(link.candidatos) == {"94", "97"}


def test_nenhum_candidato_fica_pendente_nao_erro(db_session):
    db_session.add(
        CTe(
            cte_numero="1",
            cte_serie="1",
            pagador_frete_nome="CLIENTE X",
            total=1000.0,
            data_emissao=date(2026, 7, 10),
        )
    )
    db_session.commit()

    stats = run_camada2(db_session)
    assert stats["no_candidate"] == 1
