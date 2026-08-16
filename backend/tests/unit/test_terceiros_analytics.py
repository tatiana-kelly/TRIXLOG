from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.terceiros_analytics import calcular_rentabilidade_por_terceiro


def _cte(numero, proprietario, total, cliente="X"):
    return CTe(
        cte_numero=numero,
        cte_serie="1",
        pagador_frete_nome=cliente,
        proprietario_veiculo_nome=proprietario,
        total=total,
        unidade="matriz",
    )


def test_exclui_frota_propria(db_session):
    db_session.add_all(
        [
            _cte("1", "TRIXLOG TRANSPORTES LTDA", 1000.0),
            _cte("2", "AP TUPY TRES CORACOES LTDA", 2000.0),
            _cte("3", "MAIOLINI TRANSPORTES LTDA", 500.0),
        ]
    )
    db_session.commit()

    terceiros = calcular_rentabilidade_por_terceiro(db_session)
    assert len(terceiros) == 1
    assert terceiros[0].proprietario == "MAIOLINI TRANSPORTES LTDA"


def test_agrega_receita_e_custo_por_proprietario(db_session):
    cte_a = _cte("1", "MAIOLINI TRANSPORTES LTDA", 3000.0)
    cte_b = _cte("2", "MAIOLINI TRANSPORTES LTDA", 2000.0)
    db_session.add_all([cte_a, cte_b])
    db_session.add(ContratoTransporte(contrato_numero="9", unidade="matriz", valor_total_contrato=1000.0))
    db_session.flush()
    db_session.add(ViagemLink(cte_id=cte_a.id, cte_numero="1", status="resolvido", contrato_transporte_numero="9", metodo_vinculo="manual"))
    db_session.commit()

    terceiros = calcular_rentabilidade_por_terceiro(db_session)
    t = terceiros[0]
    assert t.qtd_ctes == 2
    assert t.receita_total == 5000.0
    assert t.viagens_com_custo_alocado == 1
    assert t.viagens_pendentes == 1
    assert t.custo_alocado_total == 1000.0
    assert t.margem_total == 2000.0
