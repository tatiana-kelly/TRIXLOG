from app.models.cte import CTe
from app.services.audit_log import CALCULATION_VERSION, listar_auditorias, registrar_auditoria


def test_registra_snapshot_com_versao_de_calculo(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz"))
    db_session.commit()

    run = registrar_auditoria(db_session, trigger="manual")

    assert run.calculation_version == CALCULATION_VERSION
    assert run.metrics["receita_operacional"] == 1000.0
    assert run.trigger == "manual"


def test_listar_auditorias_mostra_diferenca_desde_a_anterior(db_session):
    db_session.add(CTe(cte_numero="1", cte_serie="1", pagador_frete_nome="A", total=1000.0, unidade="matriz"))
    db_session.commit()
    registrar_auditoria(db_session, trigger="manual")

    db_session.add(CTe(cte_numero="2", cte_serie="1", pagador_frete_nome="B", total=500.0, unidade="matriz"))
    db_session.commit()
    registrar_auditoria(db_session, trigger="import_upload")

    auditorias = listar_auditorias(db_session)
    assert len(auditorias) == 2
    mais_recente = auditorias[0]  # ordenado do mais novo pro mais antigo
    assert mais_recente["metrics"]["receita_operacional"] == 1500.0
    assert "receita_operacional" in mais_recente["mudancas_desde_auditoria_anterior"]
    diff = mais_recente["mudancas_desde_auditoria_anterior"]["receita_operacional"]
    assert diff["anterior"] == 1000.0
    assert diff["atual"] == 1500.0
    assert diff["diferenca"] == 500.0

    mais_antiga = auditorias[1]
    assert mais_antiga["mudancas_desde_auditoria_anterior"] == {}
