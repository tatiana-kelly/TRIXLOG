import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Se DATABASE_URL já vier configurada no ambiente da Vercel (Settings → Environment Variables
# → Postgres real do Supabase), usamos ela direto — dado persiste de verdade entre deploys e
# cold starts. Sem isso configurado, caímos de volta num SQLite efêmero em /tmp só para não
# quebrar: filesystem de deploy da Vercel é somente leitura fora de /tmp, então esse fallback
# NUNCA persiste (ver docs/COST_ALLOCATION.md) — é só para a demo funcionar antes da migração.
if "DATABASE_URL" not in os.environ:
    _runtime_db = Path("/tmp/trixlog.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{_runtime_db.as_posix()}"

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402

if os.environ["DATABASE_URL"].startswith("sqlite"):
    if not Path("/tmp/trixlog.db").exists():
        init_db()
else:
    init_db()  # create_all é idempotente — seguro rodar em todo cold start contra o Postgres real
