"""Copia todos os dados do SQLite local (backend/trixlog.db, já com os 18 relatórios reais
importados) para o Postgres configurado em DATABASE_URL — usado uma vez para popular o Supabase
depois da migração de Fase 2. Não inventa nem transforma nada: linha por linha, tabela por
tabela, na ordem que respeita as chaves estrangeiras (contratos antes de links)."""

from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
SQLITE_URL = f"sqlite:///{(BACKEND_DIR / 'trixlog.db').as_posix()}"

TABLE_ORDER = [
    "ctes",
    "faturas_receber",
    "contratos_transporte",
    "pagamentos_fornecedor",
    "viagem_links",
]


def main() -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL ainda aponta para SQLite — configure o Postgres antes de rodar.")

    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(settings.database_url)

    from app import models  # noqa: F401  garante que todas as tabelas estão registradas em Base

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    inspector = inspect(sqlite_engine)
    sqlite_tables = set(inspector.get_table_names())

    with SqliteSession() as sq, PgSession() as pg:
        for table_name in TABLE_ORDER:
            if table_name not in sqlite_tables:
                print(f"[pular] {table_name} não existe no SQLite de origem")
                continue
            model = next(m for m in Base.registry.mappers if m.local_table.name == table_name).class_
            linhas = sq.query(model).all()
            copiadas = 0
            for linha in linhas:
                pg.merge(linha)
                copiadas += 1
            pg.commit()
            print(f"{table_name}: {copiadas} linhas copiadas")

    print("Migração concluída.")


if __name__ == "__main__":
    main()
