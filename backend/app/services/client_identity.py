"""Normalização de nome de cliente — docs/COST_ALLOCATION.md#8b.

Problema real medido nos 18 relatórios (mai/jun/jul 2026): o mesmo cliente aparece com
grafias diferentes ("MINERVA S A" vs "MINERVA S.A.") por digitação manual na origem, o que
fragmenta rentabilidade e ranking de concentração de receita por cliente.

Regra de normalização é DETERMINÍSTICA e conservadora (maiúsculas, sem acento, sem
pontuação, colapso de espaço, e equivalência só de sufixos societários padrão — S/A, S.A.,
S A → SA; LTDA./LTDA → LTDA). Nunca usa distância de string (fuzzy match) porque isso
mescla erroneamente empresas diferentes com nomes parecidos — caso real nos dados: "CHINT
ELETRIC CO. LTD" (matriz na China) e "CHINT ELETRICOS AMERICA DO SUL LTDA" (subsidiária
brasileira) são pagadores de frete DISTINTOS e não podem ser tratados como o mesmo cliente
mesmo compartilhando a palavra "CHINT".
"""

import re
import unicodedata


def normalize_client_key(nome: str) -> str:
    """Chave de agrupamento — não usar como nome de exibição (perde acentuação/caixa)."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    s = s.upper()
    s = re.sub(r"[.,]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bS\s*/\s*A\b", "SA", s)
    s = re.sub(r"\bS\s+A\b", "SA", s)
    s = re.sub(r"\bLTDA\b\.?", "LTDA", s)
    return s


def build_canonical_names(nomes: list[str]) -> dict[str, str]:
    """Mapeia cada nome bruto para um nome canônico de exibição — o mais frequente do grupo
    (empate: o mais longo, por ter mais informação; novo empate: ordem alfabética, para ser
    determinístico)."""
    from collections import Counter

    grupos: dict[str, list[str]] = {}
    for nome in nomes:
        grupos.setdefault(normalize_client_key(nome), []).append(nome)

    contagem = Counter(nomes)
    canonical_por_chave: dict[str, str] = {}
    for chave, variantes in grupos.items():
        canonical_por_chave[chave] = max(
            set(variantes), key=lambda v: (contagem[v], len(v), v.lower() < v.lower())
        )
        # desempate final determinístico por ordem alfabética quando contagem e tamanho empatam
        melhores = [
            v
            for v in set(variantes)
            if (contagem[v], len(v)) == (contagem[canonical_por_chave[chave]], len(canonical_por_chave[chave]))
        ]
        canonical_por_chave[chave] = min(melhores)

    return {nome: canonical_por_chave[normalize_client_key(nome)] for nome in nomes}
