"""Camada 0 — join determinístico CTe <-> CartaFrete via (ctrc, unidade). Regra: mais confiável
que Camada 2, roda primeiro, e Camada 2 nunca reprocessa o que a Camada 0 já resolveu."""

from datetime import date

from app.models.carta_frete import CartaFrete
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.cost_allocation.camada0_carta_frete import run_camada0
from app.services.cost_allocation.heuristic_link import run_camada2


def test_liga_cte_a_carta_frete_por_ctrc_e_unidade(db_session):
    cte = CTe(
        cte_numero="292",
        cte_serie="1",
        pagador_frete_nome="CLIENTE X",
        unidade="matriz",
        total=4000.0,
        data_emissao=date(2026, 5, 6),
    )
    db_session.add(cte)
    db_session.add(
        CartaFrete(
            numero="53",
            ctrc="292",
            unidade="matriz",
            veiculo_placa="ARM9C03",
            frete_motorista=5700.0,
            pedagio_despesa=100.0,
        )
    )
    db_session.commit()

    result = run_camada0(db_session)

    assert result["stats"]["auto_linked"] == 1
    link = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte.id).one()
    assert link.status == "resolvido"
    assert link.metodo_vinculo == "carta_frete_direto"
    assert link.confianca_vinculo == 1.0
    assert link.custo_direto == 5800.0  # frete_motorista + pedagio_despesa


def test_nunca_liga_entre_unidades_diferentes(db_session):
    """Mesmo CTRC em matriz e filial (números se repetem entre unidades) -- carta frete de uma
    unidade nunca pode ligar num CT-e de outra."""
    cte_filial = CTe(
        cte_numero="292",
        cte_serie="1",
        pagador_frete_nome="CLIENTE X",
        unidade="filial",
        total=9999.0,
        data_emissao=date(2026, 5, 6),
    )
    db_session.add(cte_filial)
    db_session.add(
        CartaFrete(numero="53", ctrc="292", unidade="matriz", veiculo_placa="ARM9C03", frete_motorista=5700.0)
    )
    db_session.commit()

    result = run_camada0(db_session)

    assert result["stats"]["auto_linked"] == 0
    link = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte_filial.id).first()
    assert link is None


def test_camada2_nunca_reprocessa_o_que_camada0_ja_resolveu(db_session):
    cte = CTe(
        cte_numero="292",
        cte_serie="1",
        pagador_frete_nome="CLIENTE X",
        unidade="matriz",
        total=4000.0,
        data_emissao=date(2026, 5, 6),
        proprietario_veiculo_nome="TRANSPORTADORA Y",
    )
    db_session.add(cte)
    db_session.add(
        CartaFrete(numero="53", ctrc="292", unidade="matriz", veiculo_placa="ARM9C03", frete_motorista=5700.0)
    )
    db_session.commit()

    camada0_result = run_camada0(db_session)
    run_camada2(db_session, cte_ids_ja_resolvidos=camada0_result["cte_ids_resolvidos"])

    links = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte.id).all()
    assert len(links) == 1
    assert links[0].metodo_vinculo == "carta_frete_direto"
