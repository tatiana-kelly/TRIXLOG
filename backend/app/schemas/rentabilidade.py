from pydantic import BaseModel


class ViagemRentabilidadeOut(BaseModel):
    cte_numero: str
    receita: float
    custo_alocado: float | None
    margem: float | None
    status_alocacao: str


class RentabilidadeClienteOut(BaseModel):
    cliente: str
    receita_total: float
    custo_alocado_total: float
    margem_total: float
    viagens_com_custo_alocado: int
    viagens_pendentes: int
    viagens: list[ViagemRentabilidadeOut]
