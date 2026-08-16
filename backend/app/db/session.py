from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Supabase transaction pooler (porta 6543, pgbouncer) não suporta prepared statements
    # nomeados persistindo entre conexões — psycopg3 usa isso por padrão e quebra com
    # "DuplicatePreparedStatement" assim que uma conexão é reaproveitada do pool. Desliga.
    connect_args = {"prepare_threshold": None}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Colunas adicionadas a tabelas que já existiam em produção (Supabase) antes delas serem
# criadas no model — create_all() só cria tabelas NOVAS, nunca altera uma existente, então uma
# coluna nova aqui é a única forma de chegar num banco já populado sem apagar dado real. Sem
# Alembic neste projeto (deliberado, MVP) — lista curta e explícita em vez de migração formal.
_COLUNAS_ADICIONADAS_POS_CRIACAO = [
    ("viagem_links", "carta_frete_id", "VARCHAR"),
    ("viagem_links", "custo_direto", "NUMERIC(14,2)"),
]


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        with engine.begin() as conn:
            for tabela, coluna, tipo in _COLUNAS_ADICIONADAS_POS_CRIACAO:
                conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo}"))
