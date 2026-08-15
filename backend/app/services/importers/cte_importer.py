"""Importador de CT-e — aceita qualquer relatório CT-e real da TRIXLOG (matriz ou filial,
qualquer mês). Confirmado que os 18 relatórios reais de maio/junho/julho usam exatamente o
mesmo layout de colunas — nenhuma adaptação de schema foi necessária.

Rejeita (não descarta silenciosamente — reporta) linhas sem Pagador do Frete, já que esse campo
define "cliente" para toda a análise de rentabilidade (docs/COST_ALLOCATION.md#1.1).

Idempotente por arquivo: reimportar o mesmo arquivo_origem não duplica. Não usa (cte_numero,
cte_serie, unidade) sozinho como chave global — confirmado nos 18 relatórios reais que o
Número se repete entre meses (ex.: maio vai até 331, junho recomeça em 9), então dois arquivos
diferentes podem ter o mesmo número legitimamente sem serem o mesmo CT-e.
"""

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.services.importers.common import clean_str, float_id_to_str, to_date, to_float


@dataclass
class ImportResult:
    imported: int = 0
    skipped_duplicate: int = 0
    rejected: int = 0
    rejected_reasons: list[str] = field(default_factory=list)


def import_cte(path: str, db: Session, unidade: str | None = None, arquivo_origem: str | None = None) -> ImportResult:
    df = pd.read_excel(path)
    result = ImportResult()

    for idx, row in df.iterrows():
        pagador = clean_str(row.get("Pagador do Frete - Nome"))
        numero = float_id_to_str(row.get("Número"))

        if not pagador or not numero:
            result.rejected += 1
            result.rejected_reasons.append(f"linha {idx}: sem Pagador do Frete e/ou Número")
            continue

        serie = float_id_to_str(row.get("Série")) or "1"

        if arquivo_origem:
            existing = (
                db.query(CTe)
                .filter(
                    CTe.cte_numero == numero,
                    CTe.cte_serie == serie,
                    CTe.unidade == unidade,
                    CTe.arquivo_origem == arquivo_origem,
                )
                .first()
            )
            if existing:
                result.skipped_duplicate += 1
                continue

        cte = CTe(
            cte_numero=numero,
            cte_serie=serie,
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
            unidade=unidade,
            arquivo_origem=arquivo_origem,
        )
        db.add(cte)
        result.imported += 1

    db.commit()
    return result
