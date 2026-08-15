# Backlog de implementação — TRIXLOG Torre de Controle

## Fase 0 — Fundação
- [ ] Criar repositório e CI.
- [ ] Importador dos 3 relatórios reais (CT-e, Contas a Receber, Contas a Pagar) — ver `examples/*_real.xlsx`.
- [ ] Modelos de dados: `CTe`, `FaturaReceber`, `PagamentoFornecedor`, `ContratoTransporte`, `Viagem`
      (ver `docs/DATA_MODEL.md`).
- [ ] Data Quality Gate — validar CNPJ como texto (não float), completude, duplicidade.
- [ ] **Cost Allocation Engine, Camada 1**: parse determinístico de Observação (regex
      "Conhecimento NNNNNN" em Contas a Receber; "Contrato de Transporte número NN" +
      Adiantamento/Saldo em Contas a Pagar). Ver `docs/COST_ALLOCATION.md` seção 2.
- [ ] Audit trail.
- [ ] Configurar Claude Code e subagents (`.claude/agents/` já pronto).
- [ ] Autenticação e RBAC mínimo.

## Fase 1 — MVP Rentabilidade e Custo
Fontes mínimas: os 3 relatórios reais já fornecidos.

Entregas:
- [ ] Cost Allocation Engine, Camada 2 (heurística por nome/data) e Camada 3 (Reconciliation Queue manual).
- [ ] Detecção de maiores desvios de rentabilidade por cliente/viagem.
- [ ] Pareto por cliente/rota/transportador terceiro.
- [ ] Investigador, Provocador, Coordenador.
- [ ] Especialistas: `rentabilidade-cliente-viagem`, `custos-frete-terceiro`, `contas-a-receber-pagar`.
- [ ] Soluções e Ações Práticas, Conselheiro Executivo.
- [ ] Decision Queue + Reconciliation Queue.
- [ ] 3 alternativas por desvio.
- [ ] Prioridade por impacto-esforço.
- [ ] Registro de decisão.
- [ ] DRE por viagem e DRE consolidada (ver `docs/COST_ALLOCATION.md` seção 3) — com linhas
      "não alocado" explícitas onde faltar dado (folha, aluguel, etc. — não existem nas 3 planilhas).

Pergunta do MVP:
> Quais clientes/viagens dão mais e menos rentabilidade, por quê, e o que fazer com isso nesta semana?

## Fase 2 — Cotação/Orçamento de Frete
- [ ] `SolicitacaoCotacao`, `Cotacao` (venda), `CotacaoCompra` (compra a terceiro) — ver `docs/QUOTING_MODULE.md`.
- [ ] Máquina de estados de cotação (rascunho → enviada → aprovada/recusada → convertida em CT-e).
- [ ] Guardrail de margem mínima aceitável antes de converter cotação em CT-e.
- [ ] Especialista `cotacao-orcamento-frete`.
- [ ] Métricas de conversão, tempo de resposta, spread previsto x realizado.
- [ ] **Não** implementar envio automático de e-mail a cliente/transportador — cadastro manual no MVP.

## Fase 3 — Operações, Frota e Fiscal
- [ ] `operacoes-cte-ocorrencias` — atraso, avaria, extravio.
- [ ] `frota-motoristas` — produtividade própria x agregada, sinalização de risco trabalhista.
- [ ] `fiscal-cte` — consistência de CFOP, ponto de atenção do CT-e com destino exterior.
- [ ] `combustivel-pedagio`.

## Fase 4 — Comércio Exterior (bloqueada por dado)
- [ ] `comex-dta-di` já existe como agente, mas hoje só reconhece a lacuna.
- [ ] Não implementar nenhuma automação de DTA/DI/contêiner antes de: (a) confirmar com a Tatiana
      se a TRIXLOG tem operação de comex própria e recorrente, e (b) obter relatório real dessa operação.
- [ ] Se avançar, considerar reaproveitar o PRP já existente em `C:\Freight Intelligence OS`
      (agentes `desembaraco-aduaneiro-compliance`, `cambio-tributos-comex`, `custos-portuarios-armazenagem`,
      `frete-internacional-parceiros`) em vez de redesenhar do zero.

## Fase 5 — Execução inteligente
- [ ] Aprovação e workflow completo.
- [ ] SLA por ação.
- [ ] Reavaliação pós-ação.
- [ ] Aprendizado previsão versus realizado — inclusive recalibrar a heurística da Camada 2 do
      Cost Allocation Engine com as decisões manuais da Camada 3 ao longo do tempo.

## Critérios de aceite do MVP
1. Nenhuma rentabilidade por viagem/cliente é apresentada como "líquida" sem alocação de custo confirmada.
2. Todo alerta material aponta concentração (cliente, rota, transportador).
3. Todo alerta tem impacto e confiança.
4. Toda recomendação tem 3 alternativas.
5. Toda recomendação tem dono, prazo e KPI.
6. A fila ordena maior impacto/menor esforço.
7. Dados insuficientes (ex.: custo não alocado) bloqueiam certeza indevida — nunca ratear "para fechar a conta".
8. O usuário consegue rastrear a fonte (qual CT-e, qual Contrato de Transporte, qual método de vínculo).
9. Toda decisão sensível (trabalhista, fiscal, comercial abaixo da margem mínima) exige aprovação humana.

## Caso obrigatório de validação
Antes de considerar o MVP concluído, executar o fluxo sobre `examples/reconciliation_gap_case.md`
(caso de referência da lacuna de alocação de custo, dados fictícios) e sobre uma amostra real dos
3 relatórios em `examples/*_real.xlsx`. O sistema não pode concluir que uma viagem sem contrato
vinculado teve custo zero — deve declarar "não alocado" e encaminhar para a Reconciliation Queue.
