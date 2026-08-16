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


def test_cte_reivindicado_por_duas_cartas_fica_ambiguo(db_session):
    """Achado real: CT-e 309/filial aparece no CTRC de duas cartas-frete diferentes (105 e 111),
    mesmo arquivo. Erro de digitação na origem -- nenhuma das duas deve linkar automaticamente,
    cai pra Camada 2/3 como qualquer ambiguidade real (nunca escolher uma arbitrariamente)."""
    cte = CTe(cte_numero="309", cte_serie="1", pagador_frete_nome="X", unidade="filial", total=5000.0)
    db_session.add(cte)
    db_session.add(CartaFrete(numero="105", ctrc="309", unidade="filial", frete_motorista=3000.0))
    db_session.add(CartaFrete(numero="111", ctrc="309", unidade="filial", frete_motorista=4500.0))
    db_session.commit()

    result = run_camada0(db_session)

    assert result["stats"]["ambiguo_multiplas_cartas"] == 1
    assert result["stats"]["auto_linked"] == 0
    assert cte.id not in result["cte_ids_resolvidos"]
    link = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte.id).first()
    assert link is None


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


def test_carta_com_varios_ctrc_rateia_custo_por_receita(db_session):
    """Achado real (carta 69/matriz): CTRC = "371,374,376,377,380" -- uma carta cobre 5 viagens,
    custo não individualizado. Rateio proporcional à receita de cada CT-e, marcado
    carta_frete_rateado (não carta_frete_direto) para a UI deixar claro que é uma alocação."""
    cte_a = CTe(cte_numero="371", cte_serie="1", pagador_frete_nome="X", unidade="matriz", total=3000.0)
    cte_b = CTe(cte_numero="374", cte_serie="1", pagador_frete_nome="Y", unidade="matriz", total=1000.0)
    db_session.add_all([cte_a, cte_b])
    db_session.add(
        CartaFrete(numero="69", ctrc="371,374", unidade="matriz", veiculo_placa="CSK1I75", frete_motorista=4000.0)
    )
    db_session.commit()

    result = run_camada0(db_session)

    assert result["stats"]["auto_linked_rateado"] == 2
    assert result["stats"]["auto_linked_direto"] == 0

    link_a = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte_a.id).one()
    link_b = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte_b.id).one()
    assert link_a.metodo_vinculo == "carta_frete_rateado"
    assert link_a.confianca_vinculo == 0.8
    # cte_a tem 75% da receita do grupo (3000/4000) -> 75% do custo de 4000 = 3000
    assert link_a.custo_direto == 3000.0
    # cte_b tem 25% da receita do grupo (1000/4000) -> 25% do custo de 4000 = 1000
    assert link_b.custo_direto == 1000.0


def test_ctrc_com_numero_ausente_no_grupo_nao_quebra_rateio(db_session):
    """Um dos números do CTRC não corresponde a nenhum CT-e importado (fora do período, etc.) --
    o rateio segue normal só entre os CT-e's que existem, sem travar nem inventar o resto."""
    cte_a = CTe(cte_numero="371", cte_serie="1", pagador_frete_nome="X", unidade="matriz", total=3000.0)
    db_session.add(cte_a)
    db_session.add(
        CartaFrete(numero="69", ctrc="371,999", unidade="matriz", veiculo_placa="CSK1I75", frete_motorista=4000.0)
    )
    db_session.commit()

    result = run_camada0(db_session)

    assert result["stats"]["auto_linked_direto"] == 1  # só sobrou 1 CT-e real -> vira link direto
    link_a = db_session.query(ViagemLink).filter(ViagemLink.cte_id == cte_a.id).one()
    assert link_a.custo_direto == 4000.0


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
