from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.rotas_analytics import calcular_rentabilidade_por_rota


def test_agrupa_por_origem_destino(db_session):
    db_session.add_all(
        [
            CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz", local_coleta="Varginha/MG", local_entrega="Santos/SP"),
            CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=2000.0, unidade="matriz", local_coleta="Varginha/MG", local_entrega="Santos/SP"),
            CTe(cte_numero="3", cte_serie="1", pagador_frete_nome="C", total=500.0, unidade="matriz", local_coleta="Limeira/SP", local_entrega="Extrema/MG"),
        ]
    )
    db_session.commit()

    rotas = calcular_rentabilidade_por_rota(db_session)

    assert len(rotas) == 2
    top = rotas[0]
    assert top.origem == "Varginha/MG"
    assert top.destino == "Santos/SP"
    assert top.qtd_ctes == 2
    assert top.receita_total == 3000.0


def test_cte_sem_origem_ou_destino_fica_fora(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz", local_coleta=None, local_entrega="Santos/SP"))
    db_session.commit()

    rotas = calcular_rentabilidade_por_rota(db_session)
    assert rotas == []


def test_custo_confirmado_e_pendente_por_rota(db_session):
    cte_a = CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz", local_coleta="X", local_entrega="Y")
    cte_b = CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=2000.0, unidade="matriz", local_coleta="X", local_entrega="Y")
    db_session.add_all([cte_a, cte_b])
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=400.0))
    db_session.flush()
    db_session.add(ViagemLink(cte_id=cte_a.id, cte_numero="1", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual"))
    db_session.commit()

    rotas = calcular_rentabilidade_por_rota(db_session)
    r = rotas[0]
    assert r.viagens_com_custo_alocado == 1
    assert r.viagens_pendentes == 1
    assert r.custo_alocado_total == 400.0
    assert r.margem_total == 600.0
