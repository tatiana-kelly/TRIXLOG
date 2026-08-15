"""Regressão do achado real ao rodar contra os 3 arquivos: 2+ CT-e's do mesmo transportador na
mesma janela de data não podem "encontrar" e cobrar o mesmo ContratoTransporte cada um por
inteiro — isso inflava o custo alocado de LOJAS EDMIL S/A para 4x a receita antes deste fix."""

from datetime import date

from app.models.contrato_transporte import ContratoTransporte
from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor
from app.services.cost_allocation.heuristic_link import run_camada2


def test_dois_ctes_mesmo_transportador_um_so_contrato_disponivel(db_session):
    """2 CT-e's, mesmo transportador, mesma janela — só 1 contrato disponível. Um deve linkar,
    o outro tem que cair para pendente (não pode reusar o mesmo contrato duas vezes)."""
    db_session.add(
        CTe(
            cte_numero="1",
            cte_serie="1",
            pagador_frete_nome="LOJAS EDMIL S/A",
            proprietario_veiculo_nome="MAIOLINI TRANSPORTES LTDA",
            total=3430.0,
            data_emissao=date(2026, 7, 1),
        )
    )
    db_session.add(
        CTe(
            cte_numero="2",
            cte_serie="1",
            pagador_frete_nome="LOJAS EDMIL S/A",
            proprietario_veiculo_nome="MAIOLINI TRANSPORTES LTDA",
            total=5050.0,
            data_emissao=date(2026, 7, 2),
        )
    )
    db_session.add(ContratoTransporte(contrato_numero="70", fornecedor_nome="MAIOLINI TRANSPORTES LTDA", valor_total_contrato=4000.0))
    db_session.add(
        PagamentoFornecedor(
            fornecedor_nome="MAIOLINI TRANSPORTES LTDA",
            valor=4000.0,
            tipo_documento="contrato_transporte",
            numero_documento="70",
            tipo_parcela="saldo",
            dt_emissao=date(2026, 7, 1),
        )
    )
    db_session.commit()

    stats = run_camada2(db_session)

    assert stats["auto_linked"] == 1
    assert stats["candidate_already_claimed"] == 1

    from app.models.viagem_link import ViagemLink

    links = db_session.query(ViagemLink).order_by(ViagemLink.cte_numero).all()
    resolved = [link for link in links if link.status == "resolvido"]
    pending = [link for link in links if link.status == "pendente"]
    assert len(resolved) == 1
    assert len(pending) == 1
    # o contrato só aparece vinculado UMA vez no total — nunca contado duas vezes
    assert sum(1 for link in links if link.contrato_transporte_numero == "70") == 1
