"""Lança os custos fixos mensais informados diretamente pela Tatiana (2026-08-16) — nunca
aparecem em nenhum relatório importado (CT-e, Contas a Receber, Contas a Pagar, Carta Frete).
Idempotente: apaga e recria as linhas de cada (categoria, mês) antes de inserir, então pode ser
re-executado com segurança se um valor mudar no futuro.

Rodar: python -m scripts.seed_custos_fixos_mensais
"""

from app.db.session import SessionLocal, init_db
from app.models.custo_fixo_mensal import CustoFixoMensal

FONTE = "Informado diretamente pela Tatiana em 2026-08-16 — não consta em relatório de Contas a Pagar importado."

MESES = ["2026-05", "2026-06", "2026-07"]

CATEGORIAS = [
    ("aluguel_frota", "Aluguel de frota", 80_675.00),
    ("pessoal_frota", "Pessoal de frota (salário + comissão + diária)", 41_698.00),
    ("salarios_administrativos", "Salários administrativos", 28_000.00),
    ("seguro_carga", "Seguro de carga", 3_000.00),
    ("outros_custos", "Outros custos", 5_000.00),
]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        categorias_chave = [categoria for categoria, _, _ in CATEGORIAS]
        db.query(CustoFixoMensal).filter(
            CustoFixoMensal.categoria.in_(categorias_chave),
            CustoFixoMensal.mes_referencia.in_(MESES),
        ).delete(synchronize_session=False)

        for mes in MESES:
            for categoria, rotulo, valor in CATEGORIAS:
                db.add(
                    CustoFixoMensal(
                        categoria=categoria,
                        rotulo=rotulo,
                        mes_referencia=mes,
                        valor=valor,
                        fonte=FONTE,
                    )
                )
        db.commit()
        print(f"{len(MESES) * len(CATEGORIAS)} linhas de custo fixo mensal gravadas ({len(MESES)} meses x {len(CATEGORIAS)} categorias).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
