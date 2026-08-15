from app.services.importers.common import float_id_to_str


def test_float_cnpj_never_scientific_notation():
    result = float_id_to_str(6348688000181.0)
    assert result == "6348688000181"
    assert "e+" not in result.lower()


def test_float_cte_numero_never_has_dot_zero():
    result = float_id_to_str(384.0)
    assert result == "384"
    assert "." not in result


def test_none_returns_none():
    assert float_id_to_str(None) is None


def test_string_passthrough():
    assert float_id_to_str("ABC123") == "ABC123"
