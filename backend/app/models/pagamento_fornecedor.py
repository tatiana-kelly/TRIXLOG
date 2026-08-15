import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PagamentoFornecedor(Base):
    """Espelha docs/DATA_MODEL.md#PagamentoFornecedor — fonte real: examples/contas_pagar_real.xlsx (79 linhas).

    tipo_documento cobre as 3 categorias reais encontradas em Observação:
    contrato_transporte (custo de frete terceiro — só esta linha alimenta rentabilidade por
    viagem), nota_entrada (compra/insumo, não é frete), antecipacao_recebiveis (operação
    financeira, não é despesa de frete).
    """

    __tablename__ = "pagamentos_fornecedor"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    numero_documento_original: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # coluna real "Nº Documento"
    fornecedor_nome: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    centro_custo: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    favorecido_nome: Mapped[str | None] = mapped_column(String, nullable=True)
    favorecido_cnpj: Mapped[str | None] = mapped_column(String, nullable=True)

    dt_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    dt_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)

    observacao_raw: Mapped[str | None] = mapped_column(String, nullable=True)

    tipo_documento: Mapped[str] = mapped_column(String, nullable=False, default="outro")
    numero_documento: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_parcela: Mapped[str | None] = mapped_column(String, nullable=True)  # adiantamento | saldo
    filial: Mapped[str | None] = mapped_column(String, nullable=True)  # sub-código "Filial: 002" da Observação

    # matriz | filial — derivado da coluna real "Empresa" (1.0 = matriz, 2.0 = filial). Distinto
    # do campo `filial` acima, que é um sub-código textual da Observação, não a unidade contábil.
    unidade: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    arquivo_origem: Mapped[str | None] = mapped_column(String, nullable=True)
