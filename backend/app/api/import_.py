from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cost_allocation.build_contracts import build_contratos_transporte
from app.services.cost_allocation.heuristic_link import run_camada2
from app.services.importers.contas_pagar_importer import import_contas_pagar
from app.services.importers.contas_receber_importer import import_contas_receber
from app.services.importers.cte_importer import import_cte

router = APIRouter(prefix="/import", tags=["import"])

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"


@router.post("/run")
def run_import(db: Session = Depends(get_db)) -> dict:
    """Importa os 3 relatórios reais de examples/ e roda as camadas 1 e 2 do Cost Allocation
    Engine. Endpoint de conveniência para a Fase 0 — troca para upload de arquivo na Fase 1."""
    cte_result = import_cte(str(EXAMPLES_DIR / "cte_real.xlsx"), db)
    ar_result = import_contas_receber(str(EXAMPLES_DIR / "contas_receber_real.xlsx"), db)
    ap_result = import_contas_pagar(str(EXAMPLES_DIR / "contas_pagar_real.xlsx"), db)

    contratos_criados = build_contratos_transporte(db)
    camada2_stats = run_camada2(db)

    return {
        "cte": {"importados": cte_result.imported, "rejeitados": cte_result.rejected, "motivos": cte_result.rejected_reasons},
        "contas_receber": {"importados": ar_result.imported, "rejeitados": ar_result.rejected, "motivos": ar_result.rejected_reasons},
        "contas_pagar": {"importados": ap_result.imported, "rejeitados": ap_result.rejected, "motivos": ap_result.rejected_reasons},
        "contratos_transporte_construidos": contratos_criados,
        "camada2_cost_allocation": camada2_stats,
    }
