from datetime import date

from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.fleet_analytics import custos_operacionais_agregados, rentabilidade_por_veiculo


def _cte(numero, placa, dono, total, unidade="matriz", cliente="CLIENTE A", data_emissao=None):
    return CTe(
        cte_numero=numero,
        cte_serie="1",
        pagador_frete_nome=cliente,
        veiculo_placa=placa,
        proprietario_veiculo_nome=dono,
        total=total,
        unidade=unidade,
        data_emissao=data_emissao,
    )


def test_agrupa_receita_real_por_placa_frota_propria(db_session):
    db_session.add_all(
        [
            _cte("1", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 1000.0),
            _cte("2", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 2000.0, unidade="filial"),
            _cte("3", "BBB2222", "MOTORISTA TERCEIRO", 5000.0),  # frota terceira, não entra
        ]
    )
    db_session.commit()

    veiculos = rentabilidade_por_veiculo(db_session)
    assert len(veiculos) == 1
    assert veiculos[0].placa == "AAA1111"
    assert veiculos[0].viagens == 2
    assert veiculos[0].receita_total == 3000.0
    assert set(veiculos[0].unidades) == {"matriz", "filial"}


def test_custo_direto_por_veiculo_sempre_nao_determinavel(db_session):
    """Regra inegociável: sem chave real ligando combustível/manutenção a uma placa, nunca
    apresentar um custo direto por veículo como se fosse fato."""
    db_session.add(_cte("1", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 1000.0))
    db_session.commit()

    veiculos = rentabilidade_por_veiculo(db_session)
    assert veiculos[0].custo_direto_status == "nao_determinavel"


def test_dono_confirmado_manualmente_conta_como_frota_propria(db_session):
    """AP TUPY TRES CORACOES LTDA foi confirmado pela Tatiana como a própria TRIXLOG para a
    placa RME4C95 — decisão do usuário, registrada em DONOS_FROTA_PROPRIA."""
    db_session.add(_cte("1", "RME4C95", "AP TUPY TRES CORACOES LTDA", 4000.0))
    db_session.commit()

    veiculos = rentabilidade_por_veiculo(db_session)
    assert len(veiculos) == 1
    assert veiculos[0].placa == "RME4C95"


def test_rentabilidade_por_veiculo_filtra_por_mes_e_unidade(db_session):
    db_session.add_all(
        [
            _cte("1", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 1000.0, unidade="matriz", data_emissao=date(2026, 7, 10)),
            _cte("2", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 2000.0, unidade="filial", data_emissao=date(2026, 7, 15)),
            _cte("3", "AAA1111", "TRIXLOG TRANSPORTES LTDA", 500.0, unidade="matriz", data_emissao=date(2026, 6, 1)),
        ]
    )
    db_session.commit()

    veiculos_julho = rentabilidade_por_veiculo(db_session, mes_referencia="2026-07")
    assert len(veiculos_julho) == 1
    assert veiculos_julho[0].viagens == 2
    assert veiculos_julho[0].receita_total == 3000.0

    veiculos_julho_matriz = rentabilidade_por_veiculo(db_session, mes_referencia="2026-07", unidade="matriz")
    assert veiculos_julho_matriz[0].viagens == 1
    assert veiculos_julho_matriz[0].receita_total == 1000.0


def test_custos_operacionais_agregados_por_unidade_nunca_por_placa(db_session):
    db_session.add_all(
        [
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=500.0, unidade="matriz"),
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=300.0, unidade="matriz"),
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=100.0, unidade="filial"),
            PagamentoFornecedor(centro_custo="MANUTENÇÃO DE FROTA (VEÍCULOS)", valor=200.0, unidade="matriz"),
            PagamentoFornecedor(centro_custo="FRETE TERCEIRO", valor=9999.0, unidade="matriz"),  # não entra
        ]
    )
    db_session.commit()

    custos = custos_operacionais_agregados(db_session)
    combustivel_matriz = next(c for c in custos if c.categoria == "combustivel" and c.unidade == "matriz")
    assert combustivel_matriz.valor_total == 800.0
    assert combustivel_matriz.linhas == 2

    combustivel_filial = next(c for c in custos if c.categoria == "combustivel" and c.unidade == "filial")
    assert combustivel_filial.valor_total == 100.0

    manutencao_matriz = next(c for c in custos if c.categoria == "manutencao" and c.unidade == "matriz")
    assert manutencao_matriz.valor_total == 200.0

    assert not any(c.categoria not in {"combustivel", "manutencao"} for c in custos)


def test_custos_operacionais_agregados_filtra_por_mes_e_unidade(db_session):
    db_session.add_all(
        [
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=500.0, unidade="matriz", dt_emissao=date(2026, 7, 5)),
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=300.0, unidade="matriz", dt_emissao=date(2026, 6, 5)),
            PagamentoFornecedor(centro_custo="COMBUSTÍVEIS", valor=100.0, unidade="filial", dt_emissao=date(2026, 7, 5)),
        ]
    )
    db_session.commit()

    custos_julho = custos_operacionais_agregados(db_session, mes_referencia="2026-07")
    combustivel_julho_total = sum(c.valor_total for c in custos_julho if c.categoria == "combustivel")
    assert combustivel_julho_total == 600.0

    custos_julho_matriz = custos_operacionais_agregados(db_session, mes_referencia="2026-07", unidade="matriz")
    combustivel_julho_matriz = next(c for c in custos_julho_matriz if c.categoria == "combustivel")
    assert combustivel_julho_matriz.valor_total == 500.0
