"""Importador de Contas a Pagar — aceita qualquer relatório real da TRIXLOG (matriz ou filial,
qualquer mês; confirmado layout idêntico nos 18 relatórios reais de maio/junho/julho).

Classifica cada linha em 1 de 3 tipos reais de documento encontrados em Observação
(confirmado sobre as 79 linhas completas do primeiro lote, não uma amostra):
- "Contrato de Transporte número NN" (Adiantamento | Saldo) — custo de frete terceiro,
  sempre com Centro de Custo = "FRETES TERCEIROS" (20/20 linhas bateram nos dois lados).
- "Nota de Entrada número NNN" — compra/insumo (combustível, manutenção, software, etc.),
  não é custo de frete por viagem.
- "Antecipação de recebíveis" — operação financeira/factoring, não é despesa de frete.
Linha sem nenhum desses três padrões vira tipo_documento="outro".

`unidade` (matriz|filial) é derivada da coluna real "Empresa" (1.0=matriz, 2.0=filial).
Idempotente por arquivo: reimportar o mesmo arquivo_origem não duplica — Nº Documento se repete
entre meses nos relatórios reais, então não é chave global segura sozinho.
"""

import re

import pandas as pd
from sqlalchemy.orm import Session

from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.importers.common import clean_str, float_id_to_str, to_date, to_float
from app.services.importers.cte_importer import ImportResult

_CONTRATO_RE = re.compile(r"Contrato de Transporte número (\d+)", re.IGNORECASE)
_NOTA_ENTRADA_RE = re.compile(r"Nota de Entrada número (\d+)", re.IGNORECASE)
_FILIAL_RE = re.compile(r"Filial:\s*(\d+)", re.IGNORECASE)

_EMPRESA_CODE_TO_UNIDADE = {"1": "matriz", "2": "filial"}


def classify_observacao(observacao: str | None) -> dict:
    """Retorna {tipo_documento, numero_documento, tipo_parcela, filial}."""
    if not observacao:
        return {"tipo_documento": "outro", "numero_documento": None, "tipo_parcela": None, "filial": None}

    filial_match = _FILIAL_RE.search(observacao)
    filial = filial_match.group(1) if filial_match else None

    contrato_match = _CONTRATO_RE.search(observacao)
    if contrato_match:
        lower = observacao.lower()
        if "adiantamento" in lower:
            parcela = "adiantamento"
        elif "saldo" in lower:
            parcela = "saldo"
        else:
            parcela = None
        return {
            "tipo_documento": "contrato_transporte",
            "numero_documento": contrato_match.group(1),
            "tipo_parcela": parcela,
            "filial": filial,
        }

    nota_match = _NOTA_ENTRADA_RE.search(observacao)
    if nota_match:
        return {
            "tipo_documento": "nota_entrada",
            "numero_documento": nota_match.group(1),
            "tipo_parcela": None,
            "filial": filial,
        }

    if "antecipação de recebíveis" in observacao.lower() or "antecipacao de recebiveis" in observacao.lower():
        return {"tipo_documento": "antecipacao_recebiveis", "numero_documento": None, "tipo_parcela": None, "filial": filial}

    return {"tipo_documento": "outro", "numero_documento": None, "tipo_parcela": None, "filial": filial}


def _resolve_unidade(row, fallback: str | None) -> str | None:
    codigo = float_id_to_str(row.get("Empresa"))
    return _EMPRESA_CODE_TO_UNIDADE.get(codigo, fallback)


def import_contas_pagar(
    path: str, db: Session, unidade: str | None = None, arquivo_origem: str | None = None
) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        fornecedor = clean_str(row.get("Fornecedor"))
        if not fornecedor:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Fornecedor")
            continue

        numero_documento_original = float_id_to_str(row.get("Nº Documento"))
        row_unidade = _resolve_unidade(row, unidade)

        if numero_documento_original and arquivo_origem:
            existing = (
                db.query(PagamentoFornecedor)
                .filter(
                    PagamentoFornecedor.numero_documento_original == numero_documento_original,
                    PagamentoFornecedor.unidade == row_unidade,
                    PagamentoFornecedor.arquivo_origem == arquivo_origem,
                )
                .first()
            )
            if existing:
                result.skipped_duplicate += 1
                continue

        observacao = clean_str(row.get("Observação"))
        classification = classify_observacao(observacao)

        pagamento = PagamentoFornecedor(
            numero_documento_original=numero_documento_original,
            fornecedor_nome=fornecedor,
            centro_custo=clean_str(row.get("Centro de Custo")),
            valor=to_float(row.get("Valor")),
            favorecido_nome=clean_str(row.get("Favorecido - Nome")),
            favorecido_cnpj=float_id_to_str(row.get("Favorecido - CNPJ/CPF")),
            dt_emissao=to_date(row.get("Dt. Emissão")),
            dt_pagamento=to_date(row.get("Dt. Pagamento")),
            observacao_raw=observacao,
            tipo_documento=classification["tipo_documento"],
            numero_documento=classification["numero_documento"],
            tipo_parcela=classification["tipo_parcela"],
            filial=classification["filial"],
            unidade=row_unidade,
            arquivo_origem=arquivo_origem,
        )
        db.add(pagamento)
        result.imported += 1

    db.commit()
    return result
