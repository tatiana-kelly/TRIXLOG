"""Importa o lote completo de maio/junho/julho (matriz + filial, 18 arquivos reais) de
examples/trimestre_2026_mai_jun_jul/, usando o mesmo detector automático que a plataforma usa no
botão de importação (POST /import/upload) — dogfooding: se o detector não funcionar aqui, não
funciona na plataforma também.

Nota: os 3 arquivos soltos em examples/*_real.xlsx (cte_real.xlsx, contas_receber_real.xlsx,
contas_pagar_real.xlsx) são a MESMA entrega de dado que "* matriz julho.xlsx" deste lote (mesma
contagem de linha, confirmado) — não importar os dois, senão duplica. Este script substitui
scripts/run_real_import.py como fonte de importação real a partir de agora.

Uso: cd backend && python -m scripts.run_quarterly_import
"""

import json
from pathlib import Path

from app.db.session import Base, SessionLocal, engine
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink
from app.services.cost_allocation.build_contracts import build_contratos_transporte
from app.services.cost_allocation.heuristic_link import run_camada2
from app.services.importers.contas_pagar_importer import import_contas_pagar
from app.services.importers.contas_receber_importer import import_contas_receber
from app.services.importers.cte_importer import import_cte
from app.services.importers.report_detector import detect_report_type, guess_unidade_from_filename
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente

TRIMESTRE_DIR = Path(__file__).resolve().parents[2] / "examples" / "trimestre_2026_mai_jun_jul"

_IMPORTERS = {
    "cte": import_cte,
    "contas_receber": import_contas_receber,
    "contas_pagar": import_contas_pagar,
}


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("=== IMPORTAÇÃO — 18 arquivos reais (maio/junho/julho, matriz+filial) ===")
        for path in sorted(TRIMESTRE_DIR.glob("*.xlsx")):
            deteccao = detect_report_type(str(path))
            if deteccao.tipo_relatorio is None:
                print(f"  [ERRO] {path.name}: {deteccao.motivo}")
                continue

            unidade = guess_unidade_from_filename(path.name)
            importer = _IMPORTERS[deteccao.tipo_relatorio]
            result = importer(str(path), db, unidade=unidade, arquivo_origem=path.name)
            print(
                f"  {path.name:38s} tipo={deteccao.tipo_relatorio:15s} unidade={unidade or '?':7s} "
                f"importados={result.imported:3d} rejeitados={result.rejected:2d} ja_importados={result.skipped_duplicate}"
            )

        print("\n=== COST ALLOCATION ENGINE ===")
        contratos_criados = build_contratos_transporte(db)
        print(f"{contratos_criados} ContratoTransporte reconstruídos (todas as unidades/meses)")

        camada2_stats = run_camada2(db)
        print(json.dumps(camada2_stats, indent=2, ensure_ascii=False))

        total_links = db.query(ViagemLink).count()
        pendentes = db.query(ViagemLink).filter(ViagemLink.status == "pendente").count()
        cobertura = (total_links - pendentes) / total_links if total_links else 0
        print(f"\n{total_links} CT-e's no total; {pendentes} pendentes de conciliação manual; cobertura automática = {cobertura:.1%}")

        print("\n=== RESUMO POR MÊS/UNIDADE ===")
        meses_unidades: dict[tuple, int] = {}
        for cte in db.query(CTe).all():
            if cte.data_emissao:
                key = (cte.data_emissao.strftime("%Y-%m"), cte.unidade)
                meses_unidades[key] = meses_unidades.get(key, 0) + 1
        for (mes, unidade), qtd in sorted(meses_unidades.items()):
            print(f"  {mes} / {unidade or '?':7s} : {qtd} CT-e's")

        print("\n=== TOP 10 CLIENTES POR RECEITA (todos os meses/unidades juntos) ===")
        for cliente in calcular_rentabilidade_por_cliente(db)[:10]:
            print(
                f"  {cliente.cliente[:40]:42s} receita=R${cliente.receita_total:>12,.2f}  "
                f"custo_alocado=R${cliente.custo_alocado_total:>10,.2f}  "
                f"viagens_alocadas={cliente.viagens_com_custo_alocado}  pendentes={cliente.viagens_pendentes}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
