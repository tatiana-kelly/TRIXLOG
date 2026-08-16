"""Importador de Carta Frete — acerto de frete com motorista/transportador terceiro (CIOT).
Ver app/models/carta_frete.py e docs/COST_ALLOCATION.md#10a.

Cada arquivo real tem uma linha de totais no rodapé (Número vazio, resto da linha são somas) —
rejeitada como as demais linhas sem Número, não é um erro de dado, é o formato real do export.

Idempotente por arquivo, mesmo padrão dos outros 3 importadores (arquivo_origem escopa o dedup,
nunca (numero, unidade) sozinho — mesmo risco de número se repetir entre meses já confirmado
nos outros relatórios)."""

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.orm import Session

from app.models.carta_frete import CartaFrete
from app.services.importers.common import clean_str, float_id_to_str, to_date, to_float


@dataclass
class ImportResult:
    imported: int = 0
    skipped_duplicate: int = 0
    rejected: int = 0
    rejected_reasons: list[str] = field(default_factory=list)


def import_carta_frete(path: str, db: Session, unidade: str | None = None, arquivo_origem: str | None = None) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        numero = float_id_to_str(row.get("Número"))
        if not numero:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Número (provável linha de totais do rodapé)")
            continue

        if arquivo_origem:
            existing = (
                db.query(CartaFrete)
                .filter(
                    CartaFrete.numero == numero,
                    CartaFrete.unidade == unidade,
                    CartaFrete.arquivo_origem == arquivo_origem,
                )
                .first()
            )
            if existing:
                result.skipped_duplicate += 1
                continue

        carta = CartaFrete(
            numero=numero,
            serie=float_id_to_str(row.get("Série")),
            data_emissao=to_date(row.get("Data de Emissão")),
            veiculo_placa=clean_str(row.get("Veículo - Placa")),
            proprietario_nome=clean_str(row.get("Proprietário - Nome")),
            motorista_nome=clean_str(row.get("Motorista - Nome")),
            ctrc=float_id_to_str(row.get("CTRC")),
            valor_total=to_float(row.get("Valor Total")),
            frete_motorista=to_float(row.get("Frete do Motorista")),
            pedagio_despesa=to_float(row.get("Pedágio (Despesa)")),
            lucro_planilha=to_float(row.get("Lucro"), default=None),
            unidade=unidade,
            arquivo_origem=arquivo_origem,
        )
        db.add(carta)
        result.imported += 1

    db.commit()
    return result
