"""Importador de Contas a Receber — aceita qualquer relatório real da TRIXLOG (matriz ou filial,
qualquer mês; confirmado layout idêntico nos 18 relatórios reais de maio/junho/julho).

Camada 1 do Cost Allocation Engine para o lado receita: extrai os números de Conhecimento
(=CT-e) citados em Observação. Padrão real confirmado em 45/46 linhas do primeiro lote:
"Fatura ref. ao Conhecimento 000024;" ou "Fatura ref. aos Conhecimentos 000377, 000380, ...;"

`unidade` (matriz|filial) é derivada da coluna real "Empresa" (1.0=matriz, 2.0=filial) quando
presente; parâmetro `unidade` só é usado como fallback se a coluna não permitir identificar.

Idempotente por arquivo: reimportar o mesmo arquivo_origem não duplica — confirmado nos 18
relatórios reais que Nº Documento se repete entre meses, então não é chave global segura.
"""

import re

import pandas as pd
from sqlalchemy.orm import Session

from app.models.fatura_receber import FaturaReceber
from app.services.importers.common import clean_str, float_id_to_str, to_date, to_float
from app.services.importers.cte_importer import ImportResult

_CONHECIMENTO_RE = re.compile(r"Conhecimentos?\s+([\d,\s]+?)(?:;|$)", re.IGNORECASE)

_EMPRESA_CODE_TO_UNIDADE = {"1": "matriz", "2": "filial"}


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


def _resolve_unidade(row, fallback: str | None) -> str | None:
    codigo = float_id_to_str(row.get("Empresa"))
    return _EMPRESA_CODE_TO_UNIDADE.get(codigo, fallback)


def import_contas_receber(
    path: str, db: Session, unidade: str | None = None, arquivo_origem: str | None = None
) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        cliente = clean_str(row.get("Cliente"))
        if not cliente:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Cliente")
            continue

        numero_documento = float_id_to_str(row.get("Nº Documento"))
        row_unidade = _resolve_unidade(row, unidade)

        if numero_documento and arquivo_origem:
            existing = (
                db.query(FaturaReceber)
                .filter(
                    FaturaReceber.numero_documento == numero_documento,
                    FaturaReceber.unidade == row_unidade,
                    FaturaReceber.arquivo_origem == arquivo_origem,
                )
                .first()
            )
            if existing:
                result.skipped_duplicate += 1
                continue

        observacao = clean_str(row.get("Observação"))
        fatura = FaturaReceber(
            numero_documento=numero_documento,
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
            unidade=row_unidade,
            arquivo_origem=arquivo_origem,
        )
        db.add(fatura)
        result.imported += 1

    db.commit()
    return result
