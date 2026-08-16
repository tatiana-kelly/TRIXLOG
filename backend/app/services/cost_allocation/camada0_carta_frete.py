"""Camada 0 — join determinístico CTe <-> CartaFrete via (CTRC, unidade). A mais confiável de
todas: não é heurística, é o mesmo número em dois relatórios diferentes da própria TRIXLOG,
validado batendo o Valor Total exato em casos reais (docs/COST_ALLOCATION.md#10a).

Roda ANTES da Camada 2 (heuristic_link.py) — resolve o que der aqui primeiro, e só passa pra
Camada 2 o que sobrar. Nunca sobrescreve nem reprocessa o que a Camada 0 já resolveu.

Custo direto = Frete do Motorista + Pedágio (Despesa) — o que a TRIXLOG efetivamente paga pelo
frete terceiro/agregado daquela viagem específica. Nunca usa o campo "Lucro" da planilha como
margem (é do sistema de origem, pode ter fórmula diferente da nossa) — a plataforma recalcula
com a fórmula própria em rentabilidade_engine.py.
"""

from sqlalchemy.orm import Session

from app.models.carta_frete import CartaFrete
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink


def run_camada0(db: Session) -> dict:
    cartas = db.query(CartaFrete).all()
    cartas_por_chave = {(c.ctrc, c.unidade): c for c in cartas if c.ctrc}

    ctes = db.query(CTe).all()
    stats = {"auto_linked": 0}
    cte_ids_resolvidos: set[str] = set()

    for cte in ctes:
        carta = cartas_por_chave.get((cte.cte_numero, cte.unidade))
        if not carta:
            continue

        custo = float(carta.frete_motorista) + float(carta.pedagio_despesa)
        link = ViagemLink(
            cte_id=cte.id,
            cte_numero=cte.cte_numero,
            carta_frete_id=carta.id,
            custo_direto=custo,
            metodo_vinculo="carta_frete_direto",
            confianca_vinculo=1.0,
            status="resolvido",
            candidatos=[],
        )
        db.add(link)
        cte_ids_resolvidos.add(cte.id)
        stats["auto_linked"] += 1

    db.commit()
    return {"stats": stats, "cte_ids_resolvidos": cte_ids_resolvidos}
