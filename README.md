# TRIXLOG Torre de Controle

Pacote de especificação (PRP) para implementação no Claude Code — torre de controle executiva
para a TRIXLOG Transportes, transportadora rodoviária de carga fechada (FTL).

## O que já está pronto
- `CLAUDE.md` com regras permanentes.
- 14 agentes especializados em `.claude/agents/` — 5 de processo + 9 de domínio real da TRIXLOG.
- Regras transversais em `.claude/rules/`.
- `docs/MASTER_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/IMPLEMENTATION_BACKLOG.md`.
- `docs/COST_ALLOCATION.md` — o documento mais importante do projeto: a lógica de 3 camadas para
  reconstruir a chave receita↔custo↔viagem que hoje não existe.
- `docs/QUOTING_MODULE.md` — módulo novo de cotação/orçamento de frete (venda e compra).
- Contratos JSON (`schemas/`), score de prioridade e roteamento por domínio (`config/`).
- 3 relatórios reais da TRIXLOG em `examples/` (`cte_real.xlsx`, `contas_receber_real.xlsx`,
  `contas_pagar_real.xlsx`) — fonte de verdade do modelo de dados, não amostra genérica do setor.
- Caso de referência `examples/reconciliation_gap_case.md`.

## Como usar
1. Abra o terminal na raiz.
2. Inicie o Claude Code.
3. Confirme que `CLAUDE.md` foi carregado.
4. Abra `CLAUDE_CODE_HANDOFF.md` e peça ao Claude Code para executar o projeto conforme o documento.

## Filosofia
**Relatório importado → chave de alocação reconstruída → causa → impacto → prioridade → solução → execução → aprendizado.**

O produto principal é a decisão, não o relatório bonito.

## O problema real (não uma suposição de mercado)
A TRIXLOG lança tudo no sistema, mas não tem rentabilidade por cliente — porque a receita (CT-e)
e o custo (Contrato de Transporte, em Contas a Pagar) usam **numerações independentes**, ligadas
hoje só por texto livre em campos de observação. Ver `docs/COST_ALLOCATION.md`.

## Projeto irmão do mesmo cliente
Existe um PRP anterior (`C:\Freight Intelligence OS`), feito sem os relatórios reais, com foco
comercial exterior mais elaborado. Mantido separado por decisão da Tatiana — não mesclar sem
instrução explícita. Ver seção final de `CLAUDE.md`.
