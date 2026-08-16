"""Custo confirmado por CT-e — extraído de dre_engine.py depois de aparecer pela 3ª vez
(rentabilidade_engine, DRE, e agora rotas/terceiros). Mesma regra sempre: custo_direto (Camada
0, join com Carta Frete) tem prioridade; se não tiver, cai pro contrato (Camada 2). Um CT-e sem
nenhuma das duas fontes não entra no mapa — quem usa isto trata a ausência como "não
determinável", nunca como custo zero."""

from sqlalchemy.orm import Session

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.viagem_link import ViagemLink


def custo_confirmado_por_cte(db: Session, ctes: list[CTe]) -> dict[str, float]:
    cte_ids = {c.id for c in ctes}
    ctes_por_id = {c.id: c for c in ctes}
    contratos_por_chave = {(c.contrato_numero, c.unidade): c for c in db.query(ContratoTransporte).all()}

    custo_por_cte: dict[str, float] = {}
    for link in db.query(ViagemLink).filter(ViagemLink.status == "resolvido").all():
        if link.cte_id not in cte_ids:
            continue
        if link.custo_direto is not None:
            custo_por_cte[link.cte_id] = float(link.custo_direto)
        elif link.contrato_transporte_numero:
            cte = ctes_por_id[link.cte_id]
            contrato = contratos_por_chave.get((link.contrato_transporte_numero, cte.unidade))
            if contrato:
                custo_por_cte[link.cte_id] = float(contrato.valor_total_contrato)

    return custo_por_cte
