import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditRun(Base):
    """Snapshot dos KPIs principais a cada reprocessamento (import) — nunca altera um número
    silenciosamente: se o resultado gerencial mudar de uma importação pra outra, a diferença
    fica registrada aqui, não só sobrescrita. Ver app/services/audit_log.py."""

    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)  # import_upload | manual
    calculation_version: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
