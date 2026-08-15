import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Filesystem de deploy da Vercel é somente leitura fora de /tmp. O banco começa vazio nesta
# demo — sem nenhum dado embutido no deploy — e é populado pela própria Tatiana através da tela
# "Importar relatórios" já existente na plataforma, reenviando os .xlsx reais direto no app já
# no ar (decisão explícita: dado real só entra pelo fluxo de upload normal, nunca embutido no
# payload de deploy nem no histórico do git). Isso também significa que o que for importado dura
# só a vida desta instância /tmp — um novo cold start começa vazio de novo. É só uma demo visual
# (ver docs/COST_ALLOCATION.md); a versão real precisa de Postgres/Supabase para persistir.
_RUNTIME_DB = Path("/tmp/trixlog.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_RUNTIME_DB.as_posix()}"

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402

if not _RUNTIME_DB.exists():
    init_db()
