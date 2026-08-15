import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ViagemLink(Base):
    """A entidade Viagem de docs/DATA_MODEL.md#Viagem — resultado do processo de conciliação,
    nunca um import direto. Uma linha por CT-e; contrato_transporte_numero é preenchido pela
    Camada 1/2/3 do Cost Allocation Engine (docs/COST_ALLOCATION.md).

    Join real é por `cte_id` (FK), não por `cte_numero` — confirmado nos 18 relatórios reais que
    o Número do CT-e se repete entre meses (ex.: maio vai até 331, junho recomeça em 9), então
    cte_numero sozinho ligaria a viagem errada assim que houvesse mais de um mês de dado.
    cte_numero fica só para exibição/rastreio.
    """

    __tablename__ = "viagem_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cte_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    cte_numero: Mapped[str] = mapped_column(String, nullable=False, index=True)
    contrato_transporte_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    metodo_vinculo: Mapped[str] = mapped_column(
        String, nullable=False, default="nao_vinculado"
    )  # regex_observacao | heuristica_placa_data | manual | nao_vinculado
    confianca_vinculo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pendente")  # pendente | resolvido
    candidatos: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
