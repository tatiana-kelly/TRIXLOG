import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.carta_frete import CartaFrete
from app.models.cte import CTe
from app.models.fatura_receber import FaturaReceber
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.cost_allocation.build_contracts import build_contratos_transporte
from app.services.cost_allocation.camada0_carta_frete import run_camada0
from app.services.cost_allocation.heuristic_link import run_camada2
from app.services.importers.carta_frete_importer import import_carta_frete
from app.services.importers.contas_pagar_importer import import_contas_pagar
from app.services.importers.contas_receber_importer import import_contas_receber
from app.services.importers.cte_importer import import_cte
from app.services.importers.report_detector import detect_report_type, guess_unidade_from_filename

router = APIRouter(prefix="/import", tags=["import"])

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"

_IMPORTERS = {
    "cte": import_cte,
    "carta_frete": import_carta_frete,
    "contas_receber": import_contas_receber,
    "contas_pagar": import_contas_pagar,
}


def _rebuild_cost_allocation(db: Session) -> dict:
    """Reconstrói ContratoTransporte e reroda o Cost Allocation Engine inteiro sobre TODO o dado
    já importado — precisa rodar de novo a cada novo arquivo, já que um CT-e importado antes
    pode agora ter candidato num contrato ou carta-frete que só chegou neste upload.

    Ordem importa: limpa ViagemLink uma vez só aqui (não dentro de cada camada, senão uma camada
    apagaria o que a anterior acabou de resolver) — Camada 0 (join direto com Carta Frete, mais
    confiável) roda primeiro, Camada 2 (heurística) só processa o que sobrou."""
    db.query(ViagemLink).delete()

    contratos_criados = build_contratos_transporte(db)
    camada0_result = run_camada0(db)
    camada2_stats = run_camada2(db, cte_ids_ja_resolvidos=camada0_result["cte_ids_resolvidos"])
    return {
        "contratos_transporte_construidos": contratos_criados,
        "camada0_carta_frete": camada0_result["stats"],
        "camada2_cost_allocation": camada2_stats,
    }


@router.post("/upload")
async def upload_reports(
    files: list[UploadFile] = File(...),
    unidade: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Botão de importação da plataforma. Aceita 1+ arquivos .xlsx de uma vez (CT-e, Contas a
    Receber, Contas a Pagar, matriz ou filial, qualquer mês — o tipo é detectado pela assinatura
    de colunas, a unidade pela coluna real "Empresa" quando existir, senão pelo nome do arquivo,
    senão pelo parâmetro `unidade` se o usuário informar).

    Sem chave de sistema de origem: cada arquivo vira `arquivo_origem` no banco, e reimportar o
    mesmo arquivo não duplica (idempotente por nome de arquivo, ver docs/COST_ALLOCATION.md#6 —
    Nº Documento e Número de CT-e se repetem entre meses, não são chave global segura).
    """
    resultados = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for upload in files:
            tmp_path = Path(tmp_dir) / upload.filename
            with tmp_path.open("wb") as f:
                shutil.copyfileobj(upload.file, f)

            deteccao = detect_report_type(str(tmp_path))
            if deteccao.tipo_relatorio is None:
                resultados.append({"arquivo": upload.filename, "erro": deteccao.motivo})
                continue

            unidade_arquivo = unidade or guess_unidade_from_filename(upload.filename)
            importer = _IMPORTERS[deteccao.tipo_relatorio]
            import_result = importer(str(tmp_path), db, unidade=unidade_arquivo, arquivo_origem=upload.filename)

            resultados.append(
                {
                    "arquivo": upload.filename,
                    "tipo_detectado": deteccao.tipo_relatorio,
                    "unidade_detectada": unidade_arquivo,
                    "importados": import_result.imported,
                    "ja_importados_antes": import_result.skipped_duplicate,
                    "rejeitados": import_result.rejected,
                    "motivos_rejeicao": import_result.rejected_reasons,
                }
            )

    cost_allocation = _rebuild_cost_allocation(db)

    return {"arquivos": resultados, **cost_allocation}


@router.get("/status")
def import_status(db: Session = Depends(get_db)) -> dict:
    """Resumo do que já foi importado — fonte de dados e período coberto, para a plataforma
    mostrar isso em cada módulo (nunca apresentar análise sem dizer de onde/quando veio)."""

    def _resumo_meses(model, date_field):
        # Agrupado em Python, não em SQL (func.strftime é SQLite-only — quebra no Postgres).
        rows = db.query(date_field, model.unidade).all()
        contagem: dict[tuple[str, str | None], int] = {}
        for data, unidade in rows:
            if not data:
                continue
            chave = (data.strftime("%Y-%m"), unidade)
            contagem[chave] = contagem.get(chave, 0) + 1
        return [{"mes": mes, "unidade": unidade, "quantidade": qtd} for (mes, unidade), qtd in contagem.items()]

    total_ctes = db.query(CTe).count()
    custo_vinculado = db.query(ViagemLink).filter(ViagemLink.status == "resolvido").count()
    pct_cobertura = round(custo_vinculado / total_ctes * 100, 1) if total_ctes else 0.0

    return {
        "cte": {"total": total_ctes, "por_mes_unidade": _resumo_meses(CTe, CTe.data_emissao)},
        "carta_frete": {"total": db.query(CartaFrete).count()},
        "contas_receber": {"total": db.query(FaturaReceber).count()},
        "contas_pagar": {"total": db.query(PagamentoFornecedor).count()},
        # Índice de cobertura de custo — nunca deixar o usuário assumir precisão que não existe.
        "cobertura_custo": {
            "ctes_com_custo_vinculado": custo_vinculado,
            "ctes_total": total_ctes,
            "pct_cobertura": pct_cobertura,
        },
    }


@router.post("/run")
def run_import_examples(db: Session = Depends(get_db)) -> dict:
    """Atalho de desenvolvimento: reimporta os 3 relatórios originais de examples/*_real.xlsx
    (mês de referência: julho, matriz). Para o fluxo real, usar POST /import/upload."""
    cte_result = import_cte(str(EXAMPLES_DIR / "cte_real.xlsx"), db, unidade="matriz", arquivo_origem="cte_real.xlsx")
    ar_result = import_contas_receber(
        str(EXAMPLES_DIR / "contas_receber_real.xlsx"), db, unidade="matriz", arquivo_origem="contas_receber_real.xlsx"
    )
    ap_result = import_contas_pagar(
        str(EXAMPLES_DIR / "contas_pagar_real.xlsx"), db, unidade="matriz", arquivo_origem="contas_pagar_real.xlsx"
    )

    cost_allocation = _rebuild_cost_allocation(db)

    return {
        "cte": {"importados": cte_result.imported, "rejeitados": cte_result.rejected, "motivos": cte_result.rejected_reasons},
        "contas_receber": {"importados": ar_result.imported, "rejeitados": ar_result.rejected, "motivos": ar_result.rejected_reasons},
        "contas_pagar": {"importados": ap_result.imported, "rejeitados": ap_result.rejected, "motivos": ap_result.rejected_reasons},
        **cost_allocation,
    }
