"""Rentabilidade de frota própria — análise separada da rentabilidade por cliente
(rentabilidade_engine.py), por veículo/placa.

Achado real (auditoria contra os 3 relatórios atuais, confirmado com a Tatiana): o CT-e carrega
a placa do veículo (`CTe.veiculo_placa`) e o dono (`CTe.proprietario_veiculo_nome`), então a
RECEITA por veículo é real e confiável. O CUSTO direto por veículo (combustível, manutenção,
pedágio) NÃO é — os lançamentos de Contas a Pagar têm posto/oficina + valor + data, mas nenhuma
referência a placa. Custo direto por veículo fica "não determinável" até chegar um relatório com
essa chave (cartão-combustível, telemetria/rastreador, ou controle de manutenção por veículo).
Pedágio pago pela frota nas estradas não existe em nenhum relatório recebido até agora — nunca
confundir com `CTe.pedagio` (pedágio cobrado do cliente dentro do frete, é receita repassada,
não custo de frota).

Nunca ratear esses custos agregados por viagem/placa sem uma chave real — violaria a regra
"nunca inventar dado" (ver CLAUDE.md e docs/COST_ALLOCATION.md).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cte import CTe
from app.models.pagamento_fornecedor import PagamentoFornecedor

# "AP TUPY TRES CORACOES LTDA" aparece como proprietário só da placa RME4C95 (8 de 13 viagens) —
# confirmado com a Tatiana em 2026-08-15 que é a própria TRIXLOG (nome/razão social usada pela
# filial para essa placa), não um agregado terceiro. Decisão do usuário, não inferência do
# sistema — ver commit que introduziu este arquivo.
DONOS_FROTA_PROPRIA = {"TRIXLOG TRANSPORTES LTDA", "AP TUPY TRES CORACOES LTDA"}


@dataclass
class VeiculoRentabilidade:
    placa: str
    unidades: list[str]
    viagens: int
    receita_total: float
    custo_direto_status: str = "nao_determinavel"  # sempre, até existir relatório com placa


@dataclass
class CustoOperacionalAgregado:
    """Custo real de combustível/manutenção, mas só no nível empresa/unidade — não há chave
    para descer a nível de veículo com os relatórios atuais (ver docstring do módulo)."""

    categoria: str
    unidade: str | None
    valor_total: float
    linhas: int


def rentabilidade_por_veiculo(db: Session) -> list[VeiculoRentabilidade]:
    ctes = db.query(CTe).filter(CTe.proprietario_veiculo_nome.in_(DONOS_FROTA_PROPRIA)).all()

    por_placa: dict[str, VeiculoRentabilidade] = {}
    for cte in ctes:
        if not cte.veiculo_placa:
            continue
        bucket = por_placa.setdefault(
            cte.veiculo_placa,
            VeiculoRentabilidade(placa=cte.veiculo_placa, unidades=[], viagens=0, receita_total=0.0),
        )
        bucket.viagens += 1
        bucket.receita_total += float(cte.total)
        if cte.unidade and cte.unidade not in bucket.unidades:
            bucket.unidades.append(cte.unidade)

    return sorted(por_placa.values(), key=lambda v: v.receita_total, reverse=True)


def custos_operacionais_agregados(db: Session) -> list[CustoOperacionalAgregado]:
    """Combustível e manutenção reais, agregados por unidade — não por placa (ver módulo)."""
    pagamentos = db.query(PagamentoFornecedor).all()

    categorias = {
        "combustivel": lambda cc: cc and "OMBUST" in cc,
        "manutencao": lambda cc: cc and "ANUTEN" in cc,
    }

    resultado: list[CustoOperacionalAgregado] = []
    for categoria, matcher in categorias.items():
        por_unidade: dict[str | None, list[PagamentoFornecedor]] = {}
        for p in pagamentos:
            if matcher(p.centro_custo):
                por_unidade.setdefault(p.unidade, []).append(p)
        for unidade, linhas in por_unidade.items():
            resultado.append(
                CustoOperacionalAgregado(
                    categoria=categoria,
                    unidade=unidade,
                    valor_total=sum(float(p.valor) for p in linhas),
                    linhas=len(linhas),
                )
            )
    return sorted(resultado, key=lambda c: (c.categoria, c.unidade or ""))
