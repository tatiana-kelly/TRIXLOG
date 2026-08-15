from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rentabilidade import RentabilidadeClienteOut
from app.services.rentabilidade_engine import calcular_rentabilidade_por_cliente

router = APIRouter(prefix="/rentabilidade", tags=["rentabilidade"])


@router.get("/por-cliente", response_model=list[RentabilidadeClienteOut])
def rentabilidade_por_cliente(db: Session = Depends(get_db)) -> list:
    return calcular_rentabilidade_por_cliente(db)
