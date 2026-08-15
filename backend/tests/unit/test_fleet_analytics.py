from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.fleet_analytics import custos_operacionais_agregados, rentabilidade_por_veiculo


def _cte(numero, placa, dono, total, unidade="matriz", cliente="CLIENTE A"):
    return CTe(
        cte_numero=numero,
        cte_serie="1",
        pagador_frete_nome=cliente,
        veiculo_placa=placa,
        proprietario_veiculo_nome=dono,
        total=total,
        unidade=unidade,
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
