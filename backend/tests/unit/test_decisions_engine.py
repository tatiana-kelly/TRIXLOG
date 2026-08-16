from datetime import date

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.decisions_engine import listar_decisoes


def _cte(numero, cliente, total, dia, mes=5):
    return CTe(
        cte_numero=numero,
        cte_serie="1",
        pagador_frete_nome=cliente,
        total=total,
        data_emissao=date(2026, mes, dia),
        unidade="matriz",
    )


def test_cliente_com_margem_confirmada_negativa_vira_decisao(db_session):
    cte = _cte("1", "CLIENTE DEFICITARIO", 1000.0, 10)
    db_session.add(cte)
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=5000.0))
    db_session.flush()
    db_session.add(
        ViagemLink(cte_id=cte.id, cte_numero="1", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual")
    )
    db_session.commit()

    decisoes = listar_decisoes(db_session)
    deficitarios = [d for d in decisoes if d.tipo == "cliente_deficitario"]
    assert len(deficitarios) == 1
    assert deficitarios[0].onde == "CLIENTE DEFICITARIO"
    assert deficitarios[0].impacto_reais == 4000.0
    assert deficitarios[0].severidade in {"critico", "atencao"}


def test_cliente_sem_custo_alocado_nunca_vira_decisao_de_prejuizo(db_session):
    """Regra inegociável: "não determinável" nunca é tratado como prejuízo confirmado."""
    db_session.add(_cte("1", "CLIENTE SEM CUSTO", 1000.0, 10))
    db_session.commit()

    decisoes = listar_decisoes(db_session)
    assert not any(d.onde == "CLIENTE SEM CUSTO" for d in decisoes if d.tipo == "cliente_deficitario")


def test_cliente_com_margem_positiva_nunca_vira_decisao(db_session):
    cte = _cte("1", "CLIENTE LUCRATIVO", 5000.0, 10)
    db_session.add(cte)
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=1000.0))
    db_session.flush()
    db_session.add(
        ViagemLink(cte_id=cte.id, cte_numero="1", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual")
    )
    db_session.commit()

    decisoes = listar_decisoes(db_session)
    assert not any(d.onde == "CLIENTE LUCRATIVO" for d in decisoes if d.tipo == "cliente_deficitario")


def test_desvio_material_vira_decisao_com_causa_como_hipotese(db_session):
    db_session.add_all(
        [
            _cte("1", "CLIENTE QUEDA", 10000.0, 10, mes=5),
            _cte("2", "CLIENTE QUEDA", 1000.0, 10, mes=6),
        ]
    )
    db_session.commit()

    decisoes = listar_decisoes(db_session)
    desvios = [d for d in decisoes if d.tipo == "desvio_receita"]
    assert len(desvios) == 1
    assert desvios[0].onde == "CLIENTE QUEDA"
    assert desvios[0].confianca == "baixa"
    assert len(desvios[0].hipoteses_causa) >= 1


def test_decisoes_ordenadas_por_severidade_depois_impacto(db_session):
    cte_a = _cte("1", "A", 100.0, 10)
    cte_b = _cte("2", "B", 100.0, 10)
    db_session.add_all([cte_a, cte_b])
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=15000.0))
    db_session.add(ContratoTransporte(contrato_numero="10", unidade="matriz", valor_total_contrato=1000.0))
    db_session.flush()
    db_session.add(ViagemLink(cte_id=cte_a.id, cte_numero="1", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual"))
    db_session.add(ViagemLink(cte_id=cte_b.id, cte_numero="2", status="resolvido", contrato_transporte_numero="10", metodo_vinculo="manual"))
    db_session.commit()

    decisoes = listar_decisoes(db_session)
    deficitarios = [d for d in decisoes if d.tipo == "cliente_deficitario"]
    assert deficitarios[0].severidade == "critico"
    assert deficitarios[0].onde == "A"
