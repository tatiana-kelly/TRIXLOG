"""Roda o import real contra os 3 relatórios de examples/ e reporta a cobertura de fato obtida
pelas Camadas 1 e 2 do Cost Allocation Engine — sem estimar de antemão, medindo.

Uso: cd backend && python -m scripts.run_real_import
"""

import json
from pathlib import Path

from app.db.session import Base, SessionLocal, engine
from app.models.cte import CTe
from app.models.fatura_receber import FaturaReceber
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink
from app.services.cost_allocation.build_contracts import build_contratos_transporte
from app.services.cost_allocation.heuristic_link import run_camada2
from app.services.importers.contas_pagar_importer import import_contas_pagar
from app.services.importers.contas_receber_importer import import_contas_receber
from app.services.importers.cte_importer import import_cte
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        cte_result = import_cte(str(EXAMPLES_DIR / "cte_real.xlsx"), db)
        ar_result = import_contas_receber(str(EXAMPLES_DIR / "contas_receber_real.xlsx"), db)
        ap_result = import_contas_pagar(str(EXAMPLES_DIR / "contas_pagar_real.xlsx"), db)

        print("=== IMPORTAÇÃO ===")
        print(f"CT-e:            {cte_result.imported} importados, {cte_result.rejected} rejeitados {cte_result.rejected_reasons}")
        print(f"Contas Receber:  {ar_result.imported} importados, {ar_result.rejected} rejeitados {ar_result.rejected_reasons}")
        print(f"Contas Pagar:    {ap_result.imported} importados, {ap_result.rejected} rejeitados {ap_result.rejected_reasons}")

        # Camada 1 (receita): cobertura de Conhecimento citado em Observação
        faturas = db.query(FaturaReceber).all()
        com_referencia = sum(1 for f in faturas if f.ctes_referenciados)
        print("\n=== CAMADA 1 — FaturaReceber -> CT-e (regex Observação) ===")
        print(f"{com_referencia}/{len(faturas)} faturas têm ao menos 1 Conhecimento referenciado")

        cte_numeros_existentes = {c.cte_numero for c in db.query(CTe).all()}
        referenciados_sem_match = 0
        total_referencias = 0
        for f in faturas:
            for numero in f.ctes_referenciados:
                total_referencias += 1
                if numero.lstrip("0") not in {n.lstrip("0") for n in cte_numeros_existentes}:
                    referenciados_sem_match += 1
        print(f"{total_referencias} referências de Conhecimento no total; {referenciados_sem_match} sem CT-e correspondente no arquivo importado")

        # Contas Pagar: distribuição real por tipo_documento
        pagamentos = db.query(PagamentoFornecedor).all()
        por_tipo: dict[str, int] = {}
        for p in pagamentos:
            por_tipo[p.tipo_documento] = por_tipo.get(p.tipo_documento, 0) + 1
        print("\n=== CONTAS A PAGAR — classificação real por tipo_documento ===")
        print(json.dumps(por_tipo, indent=2, ensure_ascii=False))

        contratos_criados = build_contratos_transporte(db)
        print(f"\n{contratos_criados} ContratoTransporte reconstruídos (Adiantamento+Saldo agrupados)")

        camada2_stats = run_camada2(db)
        print("\n=== CAMADA 2 — heurística CT-e <-> ContratoTransporte ===")
        print(json.dumps(camada2_stats, indent=2, ensure_ascii=False))

        total_links = db.query(ViagemLink).count()
        pendentes = db.query(ViagemLink).filter(ViagemLink.status == "pendente").count()
        print(f"\n{total_links} CT-e's no total; {pendentes} pendentes de conciliação manual (Camada 3) = {pendentes/total_links:.1%}")

        print("\n=== RENTABILIDADE POR CLIENTE (só com o que está confiavelmente alocado) ===")
        for cliente in calcular_rentabilidade_por_cliente(db):
            print(
                f"{cliente.cliente[:40]:42s} receita=R${cliente.receita_total:>12,.2f}  "
                f"custo_alocado=R${cliente.custo_alocado_total:>10,.2f}  "
                f"viagens_alocadas={cliente.viagens_com_custo_alocado}  pendentes={cliente.viagens_pendentes}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
