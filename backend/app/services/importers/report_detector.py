"""Detecta automaticamente o tipo de relatório (CT-e | Contas a Receber | Contas a Pagar | Carta
Frete) e a unidade (matriz | filial) de um arquivo Excel enviado pela plataforma — é o que dá
suporte ao botão de importação: o usuário só solta o arquivo, o sistema identifica o resto.

Assinatura de colunas confirmada nos relatórios reais de maio/junho/julho (matriz e filial,
mesmo layout em todos): CT-e tem "Pagador do Frete - Nome"; Contas a Receber tem "Cliente" +
"Centro de Receita"; Contas a Pagar tem "Fornecedor" + "Centro de Custo"; Carta Frete tem "CTRC"
+ "Frete do Motorista" (únicas deste relatório — nenhum dos outros 3 tem essas colunas).
"""

import re
from dataclasses import dataclass

import pandas as pd

_CTE_SIGNATURE = {"Pagador do Frete - Nome", "Número", "Série"}
_CONTAS_RECEBER_SIGNATURE = {"Cliente", "Centro de Receita"}
_CONTAS_PAGAR_SIGNATURE = {"Fornecedor", "Centro de Custo"}
_CARTA_FRETE_SIGNATURE = {"CTRC", "Frete do Motorista", "Veículo - Placa"}

_UNIDADE_FILENAME_RE = re.compile(r"\b(matriz|filial)\b", re.IGNORECASE)


@dataclass
class DetectionResult:
    tipo_relatorio: str | None  # "cte" | "contas_receber" | "contas_pagar" | None
    unidade_sugerida: str | None  # "matriz" | "filial" | None — só um palpite pelo nome do arquivo
    colunas_encontradas: int
    motivo: str


def detect_report_type(path: str) -> DetectionResult:
    try:
        columns = set(pd.read_excel(path, nrows=0).columns)
    except Exception as exc:  # noqa: BLE001 — boundary de upload: qualquer falha de leitura vira detecção negativa, não crash
        return DetectionResult(None, None, 0, f"não foi possível ler o arquivo como planilha: {exc}")

    if _CTE_SIGNATURE.issubset(columns):
        tipo = "cte"
    elif _CARTA_FRETE_SIGNATURE.issubset(columns):
        tipo = "carta_frete"
    elif _CONTAS_RECEBER_SIGNATURE.issubset(columns):
        tipo = "contas_receber"
    elif _CONTAS_PAGAR_SIGNATURE.issubset(columns):
        tipo = "contas_pagar"
    else:
        return DetectionResult(
            None,
            None,
            len(columns),
            "nenhuma assinatura de coluna conhecida (CT-e, Carta Frete, Contas a Receber, Contas a Pagar) foi encontrada",
        )

    return DetectionResult(tipo, None, len(columns), f"assinatura de {tipo} confirmada")


def guess_unidade_from_filename(filename: str) -> str | None:
    """Só um palpite auxiliar — a fonte confiável é a coluna 'Empresa' quando existe
    (ver contas_receber_importer/contas_pagar_importer). CT-e não tem essa coluna, então
    para CT-e este palpite de nome de arquivo é a única forma de saber a unidade hoje,
    a menos que o usuário informe explicitamente no upload."""
    match = _UNIDADE_FILENAME_RE.search(filename)
    return match.group(1).lower() if match else None
