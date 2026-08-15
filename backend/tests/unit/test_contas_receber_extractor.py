from app.services.importers.contas_receber_importer import extract_ctes_referenciados


def test_conhecimento_unico():
    assert extract_ctes_referenciados("Fatura ref. ao Conhecimento 000024;") == ["000024"]


def test_multiplos_conhecimentos():
    result = extract_ctes_referenciados("Fatura ref. aos Conhecimentos 000377, 000380, 000382, 000385, 000386;")
    assert result == ["000377", "000380", "000382", "000385", "000386"]


def test_preserva_zeros_a_esquerda():
    result = extract_ctes_referenciados("Fatura ref. ao Conhecimento 000024;")
    assert result[0] == "000024"
    assert result[0] != "24"


def test_observacao_ausente():
    assert extract_ctes_referenciados(None) == []
