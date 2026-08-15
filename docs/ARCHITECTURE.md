# Arquitetura proposta — TRIXLOG Torre de Controle

Mesmo molde validado no SAL Intelligence OS (Python/FastAPI + subagentes Claude Code), adaptado
ao achado real desta empresa: o gargalo não é falta de lançamento, é falta de uma chave de
alocação de custo por viagem. A arquitetura é desenhada em torno de resolver isso primeiro.

## Componentes

1. **Importadores** — leem os relatórios reais que a TRIXLOG já exporta (CT-e, Contas a Receber,
   Contas a Pagar; formato Excel/CSV do sistema de origem). Read-only sobre o sistema deles — a
   TRIXLOG só importa, a plataforma faz o resto.
2. **Canonical Data Layer** — as 3 entidades reais (`CTe`, `FaturaReceber`, `PagamentoFornecedor`)
   normalizadas, ver `docs/DATA_MODEL.md`.
3. **Data Quality Gate** — valida atualização, duplicidade, completude, CNPJ como texto (não float),
   antes de qualquer cálculo de rentabilidade.
4. **Cost Allocation Engine** — as 3 camadas de `docs/COST_ALLOCATION.md`: parse determinístico de
   Observação → heurística por nome/data → fila de conciliação manual. É o componente mais
   importante da Fase 0/1, porque toda rentabilidade por cliente depende dele.
5. **Metric Registry** — fórmulas oficiais de DRE por viagem e DRE consolidada (`docs/COST_ALLOCATION.md`
   seção 3), dono e periodicidade.
6. **Detection Engine** — desvio de rentabilidade por cliente/rota, concentração, inadimplência (DSO),
   divergência receita emitida × faturada.
7. **Agent Orchestrator** — chama os subagentes de `.claude/agents/` só conforme o roteamento de
   `config/domain-routing.yaml`.
8. **Quoting Engine** — módulo de cotação de frete (`docs/QUOTING_MODULE.md`), com guardrail de
   margem mínima antes de converter cotação em CT-e.
9. **Decision Queue** — fila de decisões, não dashboard, mesmo padrão do SAL.
10. **Reconciliation Queue** — tela específica da Camada 3 do Cost Allocation Engine: viagens sem
    vínculo automático de custo, para decisão humana rápida.
11. **Audit Trail** — toda decisão de vínculo (automática ou manual) fica registrada, vira dado de
    calibração da heurística com o tempo.

## Claude / agentes

Mesmo princípio do SAL: cada agente recebe só as ferramentas do seu domínio; o coordenador não
precisa acesso direto a dado bruto. Ver `.claude/agents/` para o roster completo (5 agentes de
processo + especialistas de domínio da TRIXLOG + o agente novo de cotação).

## Persistência sugerida

- PostgreSQL (ou SQLite na Fase 0, mesma decisão pragmática do SAL): fatos, viagens, alertas,
  decisões, cotações, auditoria.
- Nenhuma migração de dado do sistema de origem — só leitura dos relatórios que a TRIXLOG exporta.

## Backend sugerido

Python + FastAPI, SQLAlchemy, Pydantic — mesma stack do SAL Intelligence OS (decisão já validada,
não redesenhar sem motivo).

## Frontend

Torre de Controle: tela principal é a Decision Queue + a Reconciliation Queue (as duas filas de
decisão, não dashboard). Identidade visual: cores reais da TRIXLOG (verde escuro + dourado, ver
logo oficial), não paleta genérica.

## Observabilidade

Registrar por alerta/decisão: fonte do dado, método de alocação de custo usado (`metodo_vinculo`),
confiança, agente acionado, tempo, decisão humana, resultado posterior — mesmo padrão do
Audit Trail do SAL.
