# PROMPT PARA INICIAR O PROJETO NO CLAUDE CODE

Você recebeu o repositório **TRIXLOG Torre de Controle**.

Leia primeiro:
1. `CLAUDE.md`
2. `docs/MASTER_SPEC.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DATA_MODEL.md`
5. `docs/COST_ALLOCATION.md` — a lógica mais importante do projeto, leia com atenção
6. `docs/QUOTING_MODULE.md`
7. `docs/IMPLEMENTATION_BACKLOG.md`
8. `config/priority-scoring.yaml` e `config/domain-routing.yaml`
9. todos os arquivos em `.claude/rules/`
10. os agentes em `.claude/agents/`

## Objetivo
Construir uma plataforma de inteligência executiva para a TRIXLOG Transportes. A empresa já tem
CT-e, contas a receber e a pagar — só não tem rentabilidade por cliente, porque falta uma chave
de alocação de custo por viagem. Não é falta de dado, é falta de uma ponte entre dois dados que
já existem.

## Regra não negociável
Nenhuma margem/rentabilidade pode ser apresentada como "líquida" ou "final" se parte do custo não
foi alocada com confiança — ela aparece explicitamente como "não alocado", nunca como zero nem
como estimativa disfarçada de fato.

## Implementação
Comece pela Fase 0 + Fase 1 do backlog — que é inteiramente sobre resolver a alocação de custo e
gerar rentabilidade por cliente/viagem confiável. Não pule para cotação (Fase 2) ou comex (Fase 4)
antes disso.

### Stack preferida
Mesma do SAL Intelligence OS (decisão já validada, não redesenhar sem motivo):
- Python, FastAPI, Pydantic, SQLAlchemy
- SQLite na Fase 0 (trocar por Postgres depois, se necessário)
- pgvector só se/quando houver documento a indexar
- frontend simples orientado a Decision Queue + Reconciliation Queue
- testes automatizados

## Primeiro incremento funcional
Implemente um caso ponta a ponta usando os relatórios reais em `examples/*_real.xlsx`:
1. importar CT-e, Contas a Receber, Contas a Pagar;
2. rodar a Camada 1 (regex) de alocação de custo e medir a cobertura real obtida;
3. para o que sobrar, simular a Camada 2 (heurística) e contar quantos casos ficam ambíguos;
4. gerar a Reconciliation Queue com o que sobrou da Camada 2;
5. calcular rentabilidade por cliente só com o que está confiavelmente alocado, marcando o resto;
6. gerar um Alert do maior desvio de rentabilidade encontrado;
7. orquestrar Investigador + `rentabilidade-cliente-viagem` + Provocador;
8. consolidar Diagnosis;
9. gerar 3 Recommendations via Soluções e Ações Práticas;
10. calcular prioridade via Conselheiro Executivo;
11. colocar em Decision Queue;
12. permitir decisão humana;
13. registrar ActionExecution.

## Critério de qualidade
Crie testes que falhem se:
- uma viagem sem custo alocado com confiança alta aparecer com margem calculada como se fosse líquida;
- a Camada 2 aceitar automaticamente um match com mais de 1 candidato ambíguo;
- um alerta não tiver impacto ou concentração;
- uma recomendação não tiver 3 alternativas, dono, prazo e KPI;
- `READY_FOR_DECISION` ocorrer com confiança abaixo do limite configurado;
- uma decisão sensível (trabalhista, fiscal, comercial abaixo da margem mínima) não solicitar aprovação humana;
- o sistema recomendar aumento de estrutura (frota própria, pessoal) sem registrar teste de
  capacidade/produtividade/processo.

## Entrega esperada do primeiro ciclo
Antes de programar, apresente:
1. arquitetura final proposta;
2. árvore do repositório;
3. entidades e contratos;
4. fluxo de agentes;
5. plano da Fase 0;
6. plano da Fase 1;
7. riscos e decisões técnicas — inclusive a cobertura real esperada da Camada 1/2 de alocação
   de custo, medida contra os 3 relatórios reais, não estimada de antemão.

Depois, implemente em incrementos pequenos, executando testes a cada bloco.

## Caso obrigatório de validação
Antes de considerar o MVP concluído, execute o fluxo sobre `examples/reconciliation_gap_case.md`
e sobre os relatórios reais em `examples/*_real.xlsx`. O sistema não pode concluir que uma
viagem sem contrato vinculado teve custo zero, nem ratear um custo médio da rota apresentando-o
como fato — deve reconhecer a ambiguidade, encaminhar para conciliação manual, e nunca inflar
confiança artificialmente.
