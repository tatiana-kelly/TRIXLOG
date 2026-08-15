"""Testa o parser de Observação de Contas a Pagar contra os padrões reais confirmados
sobre as 79 linhas completas (não uma amostra) — ver docs/COST_ALLOCATION.md."""

from app.services.importers.contas_pagar_importer import classify_observacao


def test_contrato_transporte_adiantamento():
    result = classify_observacao(
        "Pagamento ref. ao Documento de Adiantamento de Carta Frete do Contrato de Transporte número 68;"
    )
    assert result["tipo_documento"] == "contrato_transporte"
    assert result["numero_documento"] == "68"
    assert result["tipo_parcela"] == "adiantamento"


def test_contrato_transporte_saldo():
    result = classify_observacao("Pagamento ref. ao Documento de Saldo do Contrato de Transporte número 81;")
    assert result["tipo_documento"] == "contrato_transporte"
    assert result["numero_documento"] == "81"
    assert result["tipo_parcela"] == "saldo"


def test_nota_entrada():
    result = classify_observacao("Pagamento ref. ao Documento de Nota de Entrada número 65857;")
    assert result["tipo_documento"] == "nota_entrada"
    assert result["numero_documento"] == "65857"
    assert result["tipo_parcela"] is None


def test_antecipacao_recebiveis():
    result = classify_observacao("Antecipação de recebíveis 24/7/2026.")
    assert result["tipo_documento"] == "antecipacao_recebiveis"


def test_filial_extraida():
    result = classify_observacao("Pagamento ref. ao Documento de Nota de Entrada número 2304; Filial: 002;")
    assert result["filial"] == "002"


def test_observacao_vazia():
    result = classify_observacao(None)
    assert result["tipo_documento"] == "outro"
