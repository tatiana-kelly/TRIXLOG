import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CTe(Base):
    """Espelha docs/DATA_MODEL.md#CTe — fonte real: examples/cte_real.xlsx (68 linhas).

    Chave de negócio (cte_numero, cte_serie) — NÃO é a mesma série de ContratoTransporte
    (ver docs/COST_ALLOCATION.md): essa é a raiz do problema de rentabilidade por cliente.
    """

    __tablename__ = "ctes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cte_numero: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cte_serie: Mapped[str] = mapped_column(String, nullable=False)
    cte_tipo: Mapped[str] = mapped_column(String, nullable=True)  # "CT-e" | "67"

    data_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    local_coleta: Mapped[str | None] = mapped_column(String, nullable=True)
    local_entrega: Mapped[str | None] = mapped_column(String, nullable=True)
    cfop: Mapped[str | None] = mapped_column(String, nullable=True)

    pagador_frete_nome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    remetente_nome: Mapped[str | None] = mapped_column(String, nullable=True)
    remetente_cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    remetente_cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    destinatario_nome: Mapped[str | None] = mapped_column(String, nullable=True)
    destinatario_cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    destinatario_cnpj: Mapped[str | None] = mapped_column(String, nullable=True)

    proprietario_veiculo_nome: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    veiculo_placa: Mapped[str | None] = mapped_column(String, nullable=True)
    motorista_nome: Mapped[str | None] = mapped_column(String, nullable=True)

    valor_frete: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    valor_frete_peso: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    pedagio: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    modal: Mapped[str | None] = mapped_column(String, nullable=True)
    entrega_status: Mapped[str | None] = mapped_column(String, nullable=True)  # coluna real "Entrega"
    data_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    ultima_ocorrencia: Mapped[str | None] = mapped_column(String, nullable=True)

    # matriz | filial — CT-e não tem coluna "Empresa" própria; vem do arquivo de origem
    # (nome do arquivo exportado, ex. "CT-e matriz julho.xlsx") no momento da importação.
    unidade: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    arquivo_origem: Mapped[str | None] = mapped_column(String, nullable=True)
