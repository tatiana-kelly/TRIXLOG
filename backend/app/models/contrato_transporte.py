import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ContratoTransporte(Base):
    """Reconstruída (não é planilha própria) agrupando PagamentoFornecedor por
    numero_documento onde tipo_documento="contrato_transporte". Ver docs/COST_ALLOCATION.md#1.4.
    """

    __tablename__ = "contratos_transporte"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contrato_numero: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    fornecedor_nome: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_adiantamento: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    valor_saldo: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    valor_total_contrato: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
