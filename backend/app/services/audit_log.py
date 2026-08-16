"""Audit log real — grava um snapshot dos KPIs principais (escopo "todo o período", matriz +
filial) a cada reprocessamento do Cost Allocation Engine. Nunca altera um número silenciosamente:
se a próxima importação mudar o resultado gerencial (ou qualquer outra métrica), a diferença fica
registrada, não só sobrescrita — ver docs/COST_ALLOCATION.md.

calculation_version muda quando a FÓRMULA da DRE muda (não a cada import) — permite saber se uma
diferença entre duas auditorias veio de dado novo ou de regra de cálculo nova."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.audit_run import AuditRun
from app.services.dre_engine import calcular_dre
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente

CALCULATION_VERSION = "DRE_v1.0"


def _snapshot_metrics(db: Session) -> dict:
    dre = calcular_dre(db)
    clientes = calcular_rentabilidade_por_cliente(db)
    total_viagens = sum(c.viagens_com_custo_alocado + c.viagens_pendentes for c in clientes)
    viagens_alocadas = sum(c.viagens_com_custo_alocado for c in clientes)

    return {
        "receita_operacional": dre.receita_operacional,
        "custo_frete_terceiro_confirmado": dre.custo_frete_terceiro_confirmado,
        "combustivel": dre.combustivel,
        "manutencao": dre.manutencao,
        "margem_contribuicao": dre.margem_contribuicao,
        "total_despesas_operacionais": dre.total_despesas_operacionais,
        "resultado_operacional": dre.resultado_operacional,
        "despesas_financeiras": dre.despesas_financeiras,
        "resultado_gerencial": dre.resultado_gerencial,
        "cobertura_custo_pct": round(viagens_alocadas / total_viagens * 100, 1) if total_viagens else 0.0,
    }


def registrar_auditoria(db: Session, trigger: str = "manual") -> AuditRun:
    run = AuditRun(
        executed_at=datetime.now(UTC),
        trigger=trigger,
        calculation_version=CALCULATION_VERSION,
        metrics=_snapshot_metrics(db),
    )
    db.add(run)
    db.commit()
    return run


def listar_auditorias(db: Session, limite: int = 20) -> list[dict]:
    """Cada item traz o snapshot e a diferença em relação à auditoria anterior — nunca esconde
    uma métrica que mudou entre dois reprocessamentos."""
    runs = db.query(AuditRun).order_by(AuditRun.executed_at.desc()).limit(limite).all()
    resultado = []
    for i, run in enumerate(runs):
        anterior = runs[i + 1] if i + 1 < len(runs) else None
        diffs = {}
        if anterior:
            for chave, valor in run.metrics.items():
                valor_anterior = anterior.metrics.get(chave)
                if valor_anterior is not None and abs(valor - valor_anterior) > 0.01:
                    diffs[chave] = {"anterior": valor_anterior, "atual": valor, "diferenca": valor - valor_anterior}
        resultado.append(
            {
                "id": run.id,
                "executed_at": run.executed_at.isoformat(),
                "trigger": run.trigger,
                "calculation_version": run.calculation_version,
                "metrics": run.metrics,
                "mudancas_desde_auditoria_anterior": diffs,
            }
        )
    return resultado
