from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CustoFixoMensal(Base):
    """Custo operacional recorrente informado diretamente pela Tatiana — nunca aparece em nenhum
    relatório importado (CT-e, Contas a Receber, Contas a Pagar, Carta Frete). Sem chave de
    unidade (matriz/filial): o valor é o total consolidado da empresa, então só entra na DRE na
    visão consolidada (sem filtro de unidade) — ver app/services/dre_engine.py.

    "salarios_administrativos" substitui (não soma sobre) o que antes vinha da categoria real
    "ADMINISTRATIVAS - MÃO DE OBRA" de Contas a Pagar — confirmado com a Tatiana em 2026-08-16
    que R$ 28.000,00/mês é o valor real e completo da folha administrativa, e o que estava em
    Contas a Pagar era parcial/incompleto (ausente por completo em julho/2026)."""

    __tablename__ = "custos_fixos_mensais"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    rotulo: Mapped[str] = mapped_column(String, nullable=False)
    mes_referencia: Mapped[str] = mapped_column(String, nullable=False)  # "YYYY-MM"
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fonte: Mapped[str] = mapped_column(String, nullable=False)
