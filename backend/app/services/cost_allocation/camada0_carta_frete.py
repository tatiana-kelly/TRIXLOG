"""Camada 0 — join determinístico CTe <-> CartaFrete via (CTRC, unidade). A mais confiável de
todas: não é heurística, é o mesmo número em dois relatórios diferentes da própria TRIXLOG,
validado batendo o Valor Total exato em casos reais (docs/COST_ALLOCATION.md#10a).

Roda ANTES da Camada 2 (heuristic_link.py) — resolve o que der aqui primeiro, e só passa pra
Camada 2 o que sobrar. Nunca sobrescreve nem reprocessa o que a Camada 0 já resolveu.

Custo = Frete do Motorista + Pedágio (Despesa) — o que a TRIXLOG efetivamente paga pelo frete
terceiro/agregado daquela(s) viagem(ns). Nunca usa o campo "Lucro" da planilha como margem (é do
sistema de origem, pode ter fórmula diferente da nossa) — a plataforma recalcula com a fórmula
própria em rentabilidade_engine.py.

Uma carta-frete pode cobrir várias viagens — confirmado real nos dados (carta 69/matriz:
CTRC="371,374,376,377,380"; carta 77/matriz: 13 CT-e's numa linha só). Quando isso acontece, o
custo não vem individualizado por CT-e, então rateamos proporcionalmente à receita de cada CT-e
dentro do grupo (mesma regra gerencial documentada no PRP original da Tatiana, seção 16):
participação = receita_cte / receita_total_dos_ctes_da_carta; custo_cte = custo_carta ×
participação. Isso é uma regra de alocação transparente, não uma invenção de dado — por isso o
metodo_vinculo fica marcado "carta_frete_rateado" (confiança 0.8, menor que o link 1:1 direto)
em vez de "carta_frete_direto".

Achado real (nunca ignorar): um mesmo CT-e pode ser referenciado pelo CTRC de DUAS cartas-frete
diferentes (ex.: CT-e 309/filial aparece na carta 105 E na carta 111, mesmo arquivo real) — erro
de digitação/duplicidade na origem, não um caso resolvível automaticamente. Nesses casos o CT-e
NÃO é auto-linkado por nenhuma das duas — cai pra Camada 2/3, igual a qualquer ambiguidade real."""

from sqlalchemy.orm import Session

from app.models.carta_frete import CartaFrete
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink


def run_camada0(db: Session) -> dict:
    cartas = db.query(CartaFrete).all()
    ctes = db.query(CTe).all()
    ctes_por_chave = {(c.cte_numero, c.unidade): c for c in ctes}

    # Passo 1: para cada CT-e candidato, coletar TODAS as cartas-frete que o referenciam —
    # precisa disso antes de linkar qualquer coisa, pra detectar CT-e reivindicado por >1 carta.
    candidatos_por_cte: dict[str, list[tuple[CartaFrete, list[CTe]]]] = {}
    for carta in cartas:
        if not carta.ctrc:
            continue
        ctrc_numeros = [n.strip() for n in carta.ctrc.split(",") if n.strip()]
        ctes_da_carta = [ctes_por_chave[(n, carta.unidade)] for n in ctrc_numeros if (n, carta.unidade) in ctes_por_chave]
        for cte in ctes_da_carta:
            candidatos_por_cte.setdefault(cte.id, []).append((carta, ctes_da_carta))

    stats = {"auto_linked_direto": 0, "auto_linked_rateado": 0, "ambiguo_multiplas_cartas": 0}
    cte_ids_resolvidos: set[str] = set()

    for cte_id, candidatos in candidatos_por_cte.items():
        if len(candidatos) > 1:
            stats["ambiguo_multiplas_cartas"] += 1
            continue

        carta, ctes_da_carta = candidatos[0]
        cte = next(c for c in ctes_da_carta if c.id == cte_id)
        custo_total_carta = float(carta.frete_motorista) + float(carta.pedagio_despesa)

        if len(ctes_da_carta) == 1:
            custo_direto = custo_total_carta
            metodo = "carta_frete_direto"
            confianca = 1.0
            stats["auto_linked_direto"] += 1
        else:
            receita_total_grupo = sum(float(c.total) for c in ctes_da_carta)
            participacao = (float(cte.total) / receita_total_grupo) if receita_total_grupo else (1 / len(ctes_da_carta))
            custo_direto = round(custo_total_carta * participacao, 2)
            metodo = "carta_frete_rateado"
            confianca = 0.8
            stats["auto_linked_rateado"] += 1

        db.add(
            ViagemLink(
                cte_id=cte.id,
                cte_numero=cte.cte_numero,
                carta_frete_id=carta.id,
                custo_direto=custo_direto,
                metodo_vinculo=metodo,
                confianca_vinculo=confianca,
                status="resolvido",
                candidatos=[],
            )
        )
        cte_ids_resolvidos.add(cte.id)

    db.commit()
    stats["auto_linked"] = stats["auto_linked_direto"] + stats["auto_linked_rateado"]
    return {"stats": stats, "cte_ids_resolvidos": cte_ids_resolvidos}
