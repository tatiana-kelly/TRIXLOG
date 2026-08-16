import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CartaFrete(Base):
    """Acerto de frete com motorista/transportador terceiro — documento real (CIOT), fonte:
    relatório "Carta Frete" (6 arquivos reais, mai/jun/jul, matriz+filial). Ver
    docs/COST_ALLOCATION.md#10a — é a Camada 0 do Cost Allocation Engine: join determinístico
    com CTe via (ctrc, unidade), validado batendo o valor exato do CT-e em casos reais (nunca
    fuzzy/heurístico). Cobre só frete terceiro/agregado — zero interseção de placa com a frota
    própria, confirmado (ver app/services/fleet_analytics.py).
    """

    __tablename__ = "cartas_frete"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    numero: Mapped[str] = mapped_column(String, nullable=False, index=True)
    serie: Mapped[str | None] = mapped_column(String, nullable=True)
    data_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)

    veiculo_placa: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    proprietario_nome: Mapped[str | None] = mapped_column(String, nullable=True)
    motorista_nome: Mapped[str | None] = mapped_column(String, nullable=True)

    # CTRC — chave real de ligação com CTe.cte_numero (mesma unidade). Ver Camada 0.
    ctrc: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    valor_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    frete_motorista: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    pedagio_despesa: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    lucro_planilha: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )  # informativo — nunca usado como margem da plataforma, recalculamos com fórmula própria

    unidade: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    arquivo_origem: Mapped[str | None] = mapped_column(String, nullable=True)
