from datetime import date

from app.models.cte import CTe
from app.services.monthly_analytics import (
    comparativo_mensal,
    detectar_desvios_mensais,
    listar_meses_disponiveis,
    rentabilidade_mensal_por_cliente,
)


def _cte(numero, cliente, total, mes_dia, unidade="matriz"):
    return CTe(
        cte_numero=numero,
        cte_serie="1",
        pagador_frete_nome=cliente,
        total=total,
        data_emissao=mes_dia,
        unidade=unidade,
    )


def test_listar_meses_disponiveis(db_session):
    db_session.add_all(
        [
            _cte("1", "CLIENTE A", 1000.0, date(2026, 5, 10)),
            _cte("2", "CLIENTE A", 1200.0, date(2026, 6, 10)),
        ]
    )
    db_session.commit()

    assert listar_meses_disponiveis(db_session) == ["2026-05", "2026-06"]


def test_rentabilidade_mensal_filtra_por_mes(db_session):
    db_session.add_all(
        [
            _cte("1", "CLIENTE A", 1000.0, date(2026, 5, 10)),
            _cte("2", "CLIENTE A", 5000.0, date(2026, 6, 10)),
        ]
    )
    db_session.commit()

    maio = rentabilidade_mensal_por_cliente(db_session, "2026-05")
    assert len(maio) == 1
    assert maio[0].receita_total == 1000.0

    junho = rentabilidade_mensal_por_cliente(db_session, "2026-06")
    assert junho[0].receita_total == 5000.0


def test_comparativo_mensal_uma_linha_por_cliente(db_session):
    db_session.add_all(
        [
            _cte("1", "CLIENTE A", 1000.0, date(2026, 5, 10)),
            _cte("2", "CLIENTE A", 1500.0, date(2026, 6, 10)),
            _cte("3", "CLIENTE B", 2000.0, date(2026, 6, 10)),
        ]
    )
    db_session.commit()

    comparativo = comparativo_mensal(db_session, ["2026-05", "2026-06"])
    assert len(comparativo) == 2
    cliente_a = next(c for c in comparativo if c.cliente == "CLIENTE A")
    assert cliente_a.por_mes["2026-05"].receita_total == 1000.0
    assert cliente_a.por_mes["2026-06"].receita_total == 1500.0
    assert "2026-05" not in next(c for c in comparativo if c.cliente == "CLIENTE B").por_mes


def test_desvio_material_detectado(db_session):
    db_session.add_all(
        [
            _cte("1", "CLIENTE A", 10000.0, date(2026, 5, 10)),
            _cte("2", "CLIENTE A", 2000.0, date(2026, 6, 10)),  # queda de 80%, R$ 8.000
        ]
    )
    db_session.commit()

    desvios = detectar_desvios_mensais(db_session, mes_atual="2026-06", mes_anterior="2026-05")
    assert len(desvios) == 1
    assert desvios[0].cliente == "CLIENTE A"
    assert desvios[0].tipo == "queda_receita"
    assert desvios[0].variacao_absoluta == -8000.0


def test_desvio_pequeno_nao_e_sinalizado(db_session):
    """Variação percentual grande mas irrelevante em R$ não deve virar desvio — regra dos dois limiares."""
    db_session.add_all(
        [
            _cte("1", "CLIENTE PEQUENO", 100.0, date(2026, 5, 10)),
            _cte("2", "CLIENTE PEQUENO", 10.0, date(2026, 6, 10)),  # -90%, mas só R$ 90
        ]
    )
    db_session.commit()

    desvios = detectar_desvios_mensais(db_session, mes_atual="2026-06", mes_anterior="2026-05")
    assert desvios == []
