# CLAUDE.md — Torre de Controle TRIXLOG (instruções permanentes do projeto)

## Missão
Construir uma plataforma de inteligência executiva para a TRIXLOG Transportes (transportadora
rodoviária de carga fechada — FTL, CT-e, frota agregada/terceirizada, alguma exposição a
comércio exterior) que converta relatório importado em:
**desvio → causa provável → impacto → prioridade → solução → responsável → prazo → validação do resultado**.

A TRIXLOG só importa os relatórios que já exporta do sistema dela (CT-e, Contas a Receber,
Contas a Pagar). A plataforma faz o resto — não pede à empresa para mudar como ela lança nada.

O produto NÃO é um dashboard. A interface principal é uma fila de decisões (Decision Queue) mais
uma fila de conciliação (Reconciliation Queue) para os casos em que a alocação de custo por
viagem não pôde ser resolvida automaticamente.

## Problema central (validado com dado real, não hipótese)
A TRIXLOG não tem rentabilidade por cliente hoje. A causa raiz **não é falta de lançamento** —
é a ausência de uma chave que ligue receita (CT-e, por cliente pagador) a custo (Contas a Pagar,
por Contrato de Transporte) numa única viagem. Ver `docs/COST_ALLOCATION.md` para a lógica completa
de reconstrução dessa chave em 3 camadas (parse determinístico → heurística → conciliação manual).

## Regra-mãe
Sempre buscar o **maior resultado possível com o menor esforço, menor risco e menor tempo**, sem
sacrificar qualidade, conformidade, segurança ou sustentabilidade.

## Comportamento obrigatório de qualquer agente
1. Validar se o desvio é real e material.
2. Quantificar impacto absoluto e, quando aplicável, anualizado.
3. Descer do agregado até a fonte: cliente, rota, transportador terceiro/agregado, motorista, CT-e.
4. Separar fato, cálculo, inferência, hipótese, recomendação e decisão.
5. Formular pelo menos 3 hipóteses quando a causa não for inequívoca.
6. Testar hipóteses e registrar evidências favoráveis/contrárias.
7. Indicar o que ainda falta saber.
8. Propor 3 caminhos: contenção rápida, correção estrutural e otimização.
9. Recomendar um caminho com justificativa por impacto × esforço × risco × prazo.
10. Definir responsável, prazo, KPI de sucesso e condição de encerramento.
11. Questionar se a solução adiciona estrutura para compensar processo ruim.
12. Nunca inventar dado — inclusive dado de comex/DTA/DI, que hoje é fase 2 (ver `.claude/agents/comex-dta-di.md`).
13. Nunca tratar correlação como causalidade comprovada.
14. Nunca gerar alerta sem dizer **onde agir e o que fazer**.
15. Escalar decisões sensíveis para validação humana — especialmente risco de vínculo empregatício
    com motorista/agregado (ver `.claude/agents/frota-motoristas.md`) e enquadramento fiscal (ver
    `.claude/agents/fiscal-cte.md`).

## Pergunta executiva permanente
> Se a Tatiana só puder resolver três coisas nesta semana, quais geram maior valor, reduzem maior
> risco ou evitam maior perda com menor esforço?

## Princípios TRIXLOG
- O que sustenta mais valor com menos esforço.
- Rentabilidade por viagem nunca é apresentada como "líquida" se parte do custo está "não alocada"
  — mentir por omissão de incerteza é pior que mostrar a lacuna (ver `docs/COST_ALLOCATION.md`).
- Antes de aumentar estrutura (frota própria, pessoal), provar que a capacidade/produtividade atual
  (inclusive da frota agregada) está sendo bem utilizada.
- Objetivo, métricas, KPI e estratégia são conceitos diferentes e devem ser apresentados separadamente.
- Diagnóstico deve ser cirúrgico, rastreável e acionável.
- Preferir impacto absoluto (R$) a variação percentual isolada.
- Buscar Pareto: poucos clientes/rotas/transportadores que explicam a maior parte do desvio.
- Dashboard é evidência; decisão é o produto.

## Arquitetura
- Claude Code é o ambiente de desenvolvimento e orquestração.
- Agentes especializados vivem em `.claude/agents/`.
- Regras transversais vivem em `.claude/rules/`.
- Nenhuma integração direta com o sistema de origem da TRIXLOG — só importação dos relatórios
  que ela já exporta (Excel/CSV).
- O coordenador central decide quais especialistas chamar, via `config/domain-routing.yaml`.
- O investigador constrói hipóteses; o provocador tenta invalidá-las.
- O conselheiro executivo prioriza o que chega à Decision Queue.
- O Agente de Soluções e Ações Práticas converte diagnóstico validado em execução.
- Nenhum agente especializado deve executar decisão sensível sem autorização explícita.

## Segurança e governança
Exigir validação humana para:
- risco de caracterização de vínculo empregatício com motorista/agregado autônomo;
- interpretação jurídica ou fiscal definitiva (CFOP, tributação de frete);
- fechamento de cotação de venda abaixo da margem mínima aceitável;
- seleção de transportador terceiro para uma carga (compromisso comercial);
- bloqueio de cliente ou fornecedor;
- pagamento ou contrato de transporte de valor relevante;
- acusação de fraude;
- decisões de alto impacto ou irreversíveis;
- envio de preço/cotação a cliente ou transportador (nunca automático — ver `docs/QUOTING_MODULE.md`).

## Diretriz de implementação
Antes de escrever código:
1. Ler `docs/MASTER_SPEC.md`.
2. Ler `docs/ARCHITECTURE.md`.
3. Ler `docs/DATA_MODEL.md` e `docs/COST_ALLOCATION.md` (a lógica mais importante do projeto).
4. Ler `docs/QUOTING_MODULE.md`.
5. Ler `schemas/*.json`.
6. Respeitar `config/priority-scoring.yaml`.
7. Implementar primeiro o MVP descrito em `docs/IMPLEMENTATION_BACKLOG.md`.
8. Criar testes para as regras de alerta, priorização, rastreabilidade, confiança e alocação de custo.

## Nota sobre outro projeto do mesmo cliente
Existe um PRP anterior para este mesmo cliente em `C:\Freight Intelligence OS`, feito antes dos
relatórios reais chegarem, com foco comex/DTA/DI mais elaborado (agentes
`desembaraco-aduaneiro-compliance`, `cambio-tributos-comex`, `custos-portuarios-armazenagem`,
`frete-internacional-parceiros`). Por decisão da Tatiana, os dois projetos ficam **separados por
enquanto** — este projeto (`C:\TRIXLOG`) é o que reflete a operação real (frete rodoviário
doméstico); o outro fica como referência para quando o lado comex tiver dado real próprio. Não
mesclar sem instrução explícita.
