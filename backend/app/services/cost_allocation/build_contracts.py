"""Camada 1 (lado custo): agrupa PagamentoFornecedor(tipo_documento='contrato_transporte') em
ContratoTransporte — Adiantamento + Saldo por numero_documento. Ver docs/COST_ALLOCATION.md#1.4.

Isto NÃO resolve o vínculo CTe <-> ContratoTransporte (não existe referência textual entre os
dois — confirmado sobre as 79 linhas reais). Esse vínculo é sempre Camada 2 ou 3.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.contrato_transporte import ContratoTransporte
from app.models.pagamento_fornecedor import PagamentoFornecedor


def build_contratos_transporte(db: Session) -> int:
    pagamentos = (
        db.query(PagamentoFornecedor)
        .filter(PagamentoFornecedor.tipo_documento == "contrato_transporte")
        .filter(PagamentoFornecedor.numero_documento.isnot(None))
        .all()
    )

    # chave (numero, unidade) — matriz e filial podem reutilizar a mesma faixa de numeração.
    grouped: dict[tuple[str, str | None], dict] = defaultdict(
        lambda: {"adiantamento": 0.0, "saldo": 0.0, "fornecedor_nome": None}
    )
    for p in pagamentos:
        key = (p.numero_documento, p.unidade)
        bucket = grouped[key]
        if p.tipo_parcela == "adiantamento":
            bucket["adiantamento"] += float(p.valor)
        elif p.tipo_parcela == "saldo":
            bucket["saldo"] += float(p.valor)
        bucket["fornecedor_nome"] = bucket["fornecedor_nome"] or p.fornecedor_nome

    db.query(ContratoTransporte).delete()

    created = 0
    for (numero, unidade), data in grouped.items():
        contrato = ContratoTransporte(
            contrato_numero=numero,
            unidade=unidade,
            fornecedor_nome=data["fornecedor_nome"],
            valor_adiantamento=data["adiantamento"],
            valor_saldo=data["saldo"],
            valor_total_contrato=data["adiantamento"] + data["saldo"],
        )
        db.add(contrato)
        created += 1

    db.commit()
    return created
