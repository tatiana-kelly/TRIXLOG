"""Importador de CT-e — fonte real: examples/cte_real.xlsx.

Rejeita (não descarta silenciosamente — reporta) linhas sem Pagador do Frete, já que esse campo
define "cliente" para toda a análise de rentabilidade (docs/COST_ALLOCATION.md#1.1).
"""

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.services.importers.common import clean_str, float_id_to_str, to_date, to_float


@dataclass
class ImportResult:
    imported: int = 0
    rejected: int = 0
    rejected_reasons: list[str] = field(default_factory=list)


def import_cte(path: str, db: Session) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        pagador = clean_str(row.get("Pagador do Frete - Nome"))
        numero = float_id_to_str(row.get("Número"))

        if not pagador or not numero:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Pagador do Frete e/ou Número")
            continue

        cte = CTe(
            cte_numero=numero,
            cte_serie=float_id_to_str(row.get("Série")) or "1",
            cte_tipo=clean_str(row.get("Tipo")),
            data_emissao=to_date(row.get("Data de Emissão")),
            local_coleta=clean_str(row.get("Local de Coleta")),
            local_entrega=clean_str(row.get("Local de Entrega")),
            cfop=float_id_to_str(row.get("CFOP")),
            pagador_frete_nome=pagador,
            remetente_nome=clean_str(row.get("Remetente - Nome")),
            remetente_cidade=clean_str(row.get("Remetente - Cidade")),
            remetente_cnpj=float_id_to_str(row.get("Remetente - CNPJ/CPF")),
            destinatario_nome=clean_str(row.get("Destinatário - Nome")),
            destinatario_cidade=clean_str(row.get("Destinatário - Cidade")),
            destinatario_cnpj=float_id_to_str(row.get("Destinatário - CNPJ/CPF")),
            proprietario_veiculo_nome=clean_str(row.get("Proprietário do Veículo - Nome")),
            veiculo_placa=clean_str(row.get("Veículo - Placa")),
            motorista_nome=clean_str(row.get("Motorista - Nome")),
            valor_frete=to_float(row.get("Valor do Frete")),
            valor_frete_peso=to_float(row.get("Valor do Frete Peso")),
            pedagio=to_float(row.get("Pedágio")),
            subtotal=to_float(row.get("Subtotal")),
            total=to_float(row.get("Total")),
            modal=clean_str(row.get("Modal")),
            entrega_status=clean_str(row.get("Entrega")),
            data_entrega=to_date(row.get("Data de Entrega")),
            ultima_ocorrencia=clean_str(row.get("Última Ocorrência")),
        )
        db.add(cte)
        result.imported += 1

    db.commit()
    return result
