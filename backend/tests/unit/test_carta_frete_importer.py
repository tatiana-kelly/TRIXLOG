from app.models.carta_frete import CartaFrete
from app.services.importers.carta_frete_importer import import_carta_frete


def _write_carta_frete_xlsx(path, rows):
    import pandas as pd

    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)


def test_importa_linhas_reais_e_rejeita_linha_de_totais_sem_numero(tmp_path, db_session):
    path = tmp_path / "carta_frete.xlsx"
    _write_carta_frete_xlsx(
        path,
        [
            {
                "Número": 53.0,
                "Série": 0.0,
                "Data de Emissão": "2026-05-06",
                "Veículo - Placa": "ARM9C03",
                "Proprietário - Nome": "JONAS SILVEIRA DE ALMEIDA",
                "Motorista - Nome": "JONAS SILVEIRA DE ALMEIDA",
                "CTRC": 292.0,
                "Valor Total": 4000,
                "Frete do Motorista": 5700.0,
                "Pedágio (Despesa)": 0.0,
                "Lucro": -1700.0,
            },
            # linha de totais do rodapé -- Número vazio, só somas nas outras colunas
            {
                "Número": None,
                "Série": None,
                "Data de Emissão": None,
                "Veículo - Placa": None,
                "Proprietário - Nome": None,
                "Motorista - Nome": None,
                "CTRC": None,
                "Valor Total": 19944,
                "Frete do Motorista": None,
                "Pedágio (Despesa)": None,
                "Lucro": 5180.45,
            },
        ],
    )

    result = import_carta_frete(str(path), db_session, unidade="matriz", arquivo_origem="carta_frete.xlsx")

    assert result.imported == 1
    assert result.rejected == 1

    cartas = db_session.query(CartaFrete).all()
    assert len(cartas) == 1
    assert cartas[0].ctrc == "292"
    assert cartas[0].veiculo_placa == "ARM9C03"
    assert cartas[0].frete_motorista == 5700.0


def test_reimportar_mesmo_arquivo_nao_duplica(tmp_path, db_session):
    path = tmp_path / "carta_frete.xlsx"
    _write_carta_frete_xlsx(
        path,
        [
            {
                "Número": 53.0,
                "Série": 0.0,
                "Data de Emissão": "2026-05-06",
                "Veículo - Placa": "ARM9C03",
                "Proprietário - Nome": "JONAS SILVEIRA DE ALMEIDA",
                "Motorista - Nome": "JONAS SILVEIRA DE ALMEIDA",
                "CTRC": 292.0,
                "Valor Total": 4000,
                "Frete do Motorista": 5700.0,
                "Pedágio (Despesa)": 0.0,
                "Lucro": -1700.0,
            }
        ],
    )

    import_carta_frete(str(path), db_session, unidade="matriz", arquivo_origem="carta_frete.xlsx")
    result2 = import_carta_frete(str(path), db_session, unidade="matriz", arquivo_origem="carta_frete.xlsx")

    assert result2.imported == 0
    assert result2.skipped_duplicate == 1
    assert db_session.query(CartaFrete).count() == 1
