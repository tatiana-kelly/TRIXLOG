"""Importador de Contas a Receber — fonte real: examples/contas_receber_real.xlsx.

Camada 1 do Cost Allocation Engine para o lado receita: extrai os números de Conhecimento
(=CT-e) citados em Observação. Padrão real confirmado em 45/46 linhas:
"Fatura ref. ao Conhecimento 000024;" ou "Fatura ref. aos Conhecimentos 000377, 000380, ...;"
"""

import re

import pandas as pd
from sqlalchemy.orm import Session

from app.models.fatura_receber import FaturaReceber
from app.services.importers.common import clean_str, to_date, to_float
from app.services.importers.cte_importer import ImportResult

_CONHECIMENTO_RE = re.compile(r"Conhecimentos?\s+([\d,\s]+?)(?:;|$)", re.IGNORECASE)


def extract_ctes_referenciados(observacao: str | None) -> list[str]:
    """Retorna os números de CT-e citados na Observação, com zeros à esquerda preservados
    (o texto já vem como string, ex. "000024" — nunca convertido para float aqui)."""
    if not observacao:
        return []
    match = _CONHECIMENTO_RE.search(observacao)
    if not match:
        return []
    numbers_blob = match.group(1)
    return [n.strip() for n in numbers_blob.split(",") if n.strip()]


def import_contas_receber(path: str, db: Session) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        cliente = clean_str(row.get("Cliente"))
        if not cliente:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Cliente")
            continue

        observacao = clean_str(row.get("Observação"))
        fatura = FaturaReceber(
            cliente_nome=cliente,
            centro_receita=clean_str(row.get("Centro de Receita")),
            valor_total=to_float(row.get("Valor Total")),
            dt_vencimento=to_date(row.get("Dt. Vencimento")),
            baixado=clean_str(row.get("Baixado")) == "Sim",
            dt_pagamento=to_date(row.get("Dt. Pagamento")),
            valor_pago=to_float(row.get("Valor Pago")),
            tipo_pagamento=clean_str(row.get("Tipo de Pagamento")),
            observacao_raw=observacao,
            ctes_referenciados=extract_ctes_referenciados(observacao),
        )
        db.add(fatura)
        result.imported += 1

    db.commit()
    return result
