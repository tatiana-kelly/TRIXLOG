from app.services.client_identity import build_canonical_names, normalize_client_key


def test_normalize_merges_punctuation_and_spacing_variants_of_sa():
    assert normalize_client_key("MINERVA S A") == normalize_client_key("MINERVA S.A.")
    assert normalize_client_key("ADICAO DISTRIBUICAO EXPRESS S/A") == normalize_client_key(
        "ADICAO DISTRIBUICAO EXPRESS S.A."
    )


def test_normalize_does_not_merge_different_companies_with_similar_names():
    # Empresas reais e distintas nos dados: matriz na China x subsidiária no Brasil.
    assert normalize_client_key("CHINT ELETRIC CO. LTD") != normalize_client_key(
        "CHINT ELETRICOS AMERICA DO SUL LTDA"
    )


def test_build_canonical_names_picks_most_frequent_spelling():
    nomes = ["MINERVA S A", "MINERVA S.A.", "MINERVA S.A.", "MINERVA S.A."]
    canonical = build_canonical_names(nomes)
    assert len(set(canonical.values())) == 1
    assert canonical["MINERVA S A"] == "MINERVA S.A."


def test_build_canonical_names_never_merges_distinct_companies():
    nomes = ["CHINT ELETRIC CO. LTD", "CHINT ELETRICOS AMERICA DO SUL LTDA"]
    canonical = build_canonical_names(nomes)
    assert canonical["CHINT ELETRIC CO. LTD"] != canonical["CHINT ELETRICOS AMERICA DO SUL LTDA"]
