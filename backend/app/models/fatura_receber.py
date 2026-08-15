import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FaturaReceber(Base):
    """Espelha docs/DATA_MODEL.md#FaturaReceber — fonte real: examples/contas_receber_real.xlsx (46 linhas)."""

    __tablename__ = "faturas_receber"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    numero_documento: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # coluna real "Nº Documento"
    cliente_nome: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    centro_receita: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    dt_vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    baixado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dt_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_pago: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    tipo_pagamento: Mapped[str | None] = mapped_column(String, nullable=True)
    observacao_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    ctes_referenciados: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # matriz | filial — derivado da coluna real "Empresa" (1.0 = matriz, 2.0 = filial,
    # confirmado nos 18 relatórios reais de maio/junho/julho).
    unidade: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    arquivo_origem: Mapped[str | None] = mapped_column(String, nullable=True)
