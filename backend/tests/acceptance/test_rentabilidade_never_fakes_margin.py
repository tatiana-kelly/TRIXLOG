"""Teste 2 de docs/ACCEPTANCE_TESTS.md — o mais importante do projeto: nunca apresentar margem
"líquida" quando o custo não foi alocado."""

from datetime import date

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente


def _make_cte(db, numero, cliente, total, data_emissao=date(2026, 7, 1)):
    cte = CTe(cte_numero=numero, cte_serie="1", pagador_frete_nome=cliente, total=total, data_emissao=data_emissao)
    db.add(cte)
    db.commit()
    return cte


def test_viagem_sem_link_fica_nao_alocada(db_session):
    _make_cte(db_session, "412", "AGROVALE INDÚSTRIA LTDA", 7200.0)
    # nenhum ViagemLink criado — simula o caso real de reconciliation_gap_case.md

    resultado = calcular_rentabilidade_por_cliente(db_session)
    assert len(resultado) == 1
    cliente = resultado[0]
    assert cliente.viagens_pendentes == 1
    assert cliente.viagens_com_custo_alocado == 0
    viagem = cliente.viagens[0]
    assert viagem.custo_alocado is None
    assert viagem.margem is None
    assert viagem.status_alocacao == "pendente"
    # nunca deve aparecer como margem = receita (custo mascarado como zero)
    assert viagem.margem != viagem.receita


def test_viagem_pendente_link_tambem_fica_nao_alocada(db_session):
    """Um ViagemLink existente mas status='pendente' (Camada 2 ambígua) não deve ser tratado
    como resolvido, mesmo que tenha candidatos sugeridos."""
    cte = _make_cte(db_session, "412", "AGROVALE INDÚSTRIA LTDA", 7200.0)
    db_session.add(
        ViagemLink(
            cte_id=cte.id,
            cte_numero="412",
            metodo_vinculo="nao_vinculado",
            confianca_vinculo=0.0,
            status="pendente",
            candidatos=["94", "97"],
        )
    )
    db_session.commit()

    resultado = calcular_rentabilidade_por_cliente(db_session)
    viagem = resultado[0].viagens[0]
    assert viagem.status_alocacao == "pendente"
    assert viagem.custo_alocado is None


def test_viagem_com_link_resolvido_calcula_margem_real(db_session):
    cte = _make_cte(db_session, "500", "FRIGORIFICO SUL LTDA", 10000.0)
    db_session.add(ContratoTransporte(contrato_numero="99", fornecedor_nome="X TRANSPORTES", valor_total_contrato=6000.0))
    db_session.add(
        ViagemLink(
            cte_id=cte.id,
            cte_numero="500",
            contrato_transporte_numero="99",
            metodo_vinculo="manual",
            confianca_vinculo=1.0,
            status="resolvido",
        )
    )
    db_session.commit()

    resultado = calcular_rentabilidade_por_cliente(db_session)
    viagem = resultado[0].viagens[0]
    assert viagem.custo_alocado == 6000.0
    assert viagem.margem == 4000.0
    assert viagem.status_alocacao == "resolvido"
