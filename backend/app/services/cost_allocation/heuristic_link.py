"""Camada 2: heurística automática CTe <-> ContratoTransporte por nome + janela de data.

Confiabilidade real, medida (não suposta): uma auditoria independente rodada contra os 3
arquivos completos achou coincidência numérica segura em só 2/79 linhas de Contas a Pagar —
ou seja, esperar que esta camada resolva a maioria dos casos é otimismo infundado. Ela existe,
mas a Camada 3 (fila de conciliação manual) é o caminho dominante na prática, não o fallback raro.

Regra de negócio (docs/COST_ALLOCATION.md#2): só aceitar automaticamente um match de Camada 2 se
houver exatamente 1 candidato dentro da janela. 0 ou 2+ candidatos sempre cai para Camada 3.

Regra adicional, corrigida após rodar contra os 3 arquivos reais: um ContratoTransporte só pode
ser reivindicado por UM CT-e. Sem isso, vários CT-e's do mesmo transportador na mesma janela de
data "encontravam" cada um, independentemente, o mesmo único contrato disponível — e o custo
daquele contrato era somado uma vez por CT-e, inflando o custo alocado de um cliente muito acima
da receita (achado real: LOJAS EDMIL S/A apareceu com custo_alocado > 4x a receita antes deste
fix). Processamos os CT-e's em ordem de data e "consumimos" o contrato assim que ele é usado —
um CT-e cujo único candidato já foi reivindicado cai para pendente (Camada 3), nunca reusa.

Regra adicional (multi-unidade): candidatos são restritos à MESMA unidade (matriz|filial) do
CT-e — confirmado nos 18 relatórios reais que matriz e filial reutilizam a mesma faixa de
numeração de contrato, então cruzar unidades geraria falso positivo. `claimed` é chaveado por
(contrato_numero, unidade), nunca só o número.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.models.viagem_link import ViagemLink


def _names_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    a_norm = a.strip().upper()
    b_norm = b.strip().upper()
    return a_norm == b_norm or a_norm in b_norm or b_norm in a_norm


def run_camada2(db: Session, cte_ids_ja_resolvidos: set[str] | None = None) -> dict:
    """cte_ids_ja_resolvidos: CT-e's já linkados pela Camada 0 (carta frete direta) — a Camada 2
    nunca reprocessa nem sobrescreve isso, só cobre o que sobrou. A limpeza de ViagemLink
    acontece uma vez só, no orquestrador (app/api/import_.py), antes de Camada 0 e Camada 2
    rodarem — não aqui, senão a Camada 2 apagaria o que a Camada 0 acabou de resolver."""
    settings = get_settings()
    window = timedelta(days=settings.camada2_max_dias_janela)
    cte_ids_ja_resolvidos = cte_ids_ja_resolvidos or set()

    contratos = db.query(ContratoTransporte).all()

    # 1 query para todos os pagamentos de contrato_transporte (era 1 por contrato — 99 round-trips
    # de rede contra Postgres remoto, invisível no SQLite local).
    pagamentos_contrato = (
        db.query(PagamentoFornecedor).filter(PagamentoFornecedor.tipo_documento == "contrato_transporte").all()
    )
    datas_por_chave: dict[tuple[str, str | None], list] = {}
    for p in pagamentos_contrato:
        if p.dt_emissao:
            datas_por_chave.setdefault((p.numero_documento, p.unidade), []).append(p.dt_emissao)

    contrato_dates: dict[tuple[str, str | None], list] = {
        (c.contrato_numero, c.unidade): datas_por_chave.get((c.contrato_numero, c.unidade), []) for c in contratos
    }

    stats = {"auto_linked": 0, "ambiguous": 0, "no_candidate": 0, "no_date": 0, "candidate_already_claimed": 0}
    claimed: set[tuple[str, str | None]] = set()

    ctes_ordenados = sorted(
        (c for c in db.query(CTe).all() if c.id not in cte_ids_ja_resolvidos),
        key=lambda c: c.data_emissao or c.cte_numero.zfill(10),
    )

    for cte in ctes_ordenados:
        candidates = []
        for c in contratos:
            if c.unidade != cte.unidade:
                continue
            if not _names_match(cte.proprietario_veiculo_nome, c.fornecedor_nome) and not _names_match(
                cte.motorista_nome, c.fornecedor_nome
            ):
                continue
            dates = contrato_dates.get((c.contrato_numero, c.unidade), [])
            if not cte.data_emissao or not dates:
                continue
            if any(abs((cte.data_emissao - d).days) <= window.days for d in dates):
                candidates.append(c)

        unclaimed_candidates = [c for c in candidates if (c.contrato_numero, c.unidade) not in claimed]

        if candidates and not unclaimed_candidates:
            link = ViagemLink(
                cte_id=cte.id,
                cte_numero=cte.cte_numero,
                metodo_vinculo="nao_vinculado",
                confianca_vinculo=0.0,
                status="pendente",
                candidatos=[c.contrato_numero for c in candidates],
            )
            stats["candidate_already_claimed"] += 1
        elif len(unclaimed_candidates) == 1:
            claimed.add((unclaimed_candidates[0].contrato_numero, unclaimed_candidates[0].unidade))
            link = ViagemLink(
                cte_id=cte.id,
                cte_numero=cte.cte_numero,
                contrato_transporte_numero=unclaimed_candidates[0].contrato_numero,
                metodo_vinculo="heuristica_placa_data",
                confianca_vinculo=0.6,
                status="resolvido",
                candidatos=[c.contrato_numero for c in candidates],
            )
            stats["auto_linked"] += 1
        elif len(unclaimed_candidates) > 1:
            link = ViagemLink(
                cte_id=cte.id,
                cte_numero=cte.cte_numero,
                metodo_vinculo="nao_vinculado",
                confianca_vinculo=0.0,
                status="pendente",
                candidatos=[c.contrato_numero for c in candidates],
            )
            stats["ambiguous"] += 1
        else:
            link = ViagemLink(
                cte_id=cte.id,
                cte_numero=cte.cte_numero,
                metodo_vinculo="nao_vinculado",
                confianca_vinculo=0.0,
                status="pendente",
                candidatos=[],
            )
            stats["no_candidate"] += 1

        db.add(link)

    db.commit()
    return stats
