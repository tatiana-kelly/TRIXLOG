# Fluxo funcional dos agentes — TRIXLOG

## Sequência padrão (casos de desvio)
Relatório importado → Cost Allocation Engine (3 camadas)
↓
Coordenador classifica o caso (`config/domain-routing.yaml`)
↓
Investigador valida, localiza e decompõe
↓
Especialistas técnicos aprofundam apenas o necessário
↓
Provocador testa o diagnóstico
↓
Investigador revisa/confirma
↓
Coordenador consolida
↓
Soluções e Ações Práticas cria alternativas executáveis
↓
Conselheiro Executivo prioriza para decisão
↓
Aprovação humana ou execução autorizada
↓
Acompanhamento
↓
Comprovação do resultado
↓
Aprendizado organizacional (inclusive recalibrando a heurística da Camada 2 do Cost Allocation Engine)

## Sequência do fluxo comercial (cotação — mais leve)
Solicitação de cotação → `cotacao-orcamento-frete` estrutura o pedido → cálculo de preço com
guardrail de margem mínima → decisão humana de enviar/fechar → (se abaixo da margem mínima)
aprovação humana obrigatória → conversão em CT-e quando aprovado. Não passa por
Investigador/Provocador por padrão — não é um desvio, é processo comercial normal.

## Responsabilidades
| Agente | Responsabilidade | Não deve fazer |
|---|---|---|
| Investigador | fatos, desvios, concentração, hipóteses e causa provável | hipótese como fato; pular para solução |
| Provocador | testar premissas, contradições, riscos e efeitos colaterais | perguntas genéricas |
| Coordenador | organizar investigação, acionar especialistas, resolver divergências | inventar consenso ou substituir validação técnica |
| Soluções e Ações Práticas | converter diagnóstico em execução | recomendar sem esforço, risco, dependências e capacidade |
| Conselheiro Executivo | priorizar decisões | transformar toda anomalia em prioridade executiva |
| Rentabilidade Cliente/Viagem | apurar margem com o que está confiavelmente alocado | apresentar margem "líquida" com custo não alocado |
| Cotação/Orçamento de Frete | estruturar e apurar o fluxo comercial | decidir ou comunicar preço a cliente/terceiro |

## Regra de coordenação
O Coordenador deve buscar a menor quantidade de investigação necessária para atingir uma decisão
suficientemente segura.

Pergunta central:
> Qual próximo passo reduz mais a incerteza ou protege mais resultado com menor esforço?

## Matriz impacto x confiança
| Impacto | Confiança | Conduta |
|---|---|---|
| Alto | Alta | Ação prioritária |
| Alto | Baixa | Contenção segura + mais investigação (ou: enviar para Reconciliation Queue se a causa for custo não alocado) |
| Baixo | Alta | Delegar/automatizar/acompanhar |
| Baixo | Baixa | Não consumir esforço excessivo |

## Regra de reversibilidade
Baixa confiança → preferir piloto, contenção, amostragem e ação reversível. Nunca fechar cotação
abaixo da margem mínima nem tomar decisão comercial/trabalhista com confiança baixa sem aprovação
humana explícita.

## Regra de encerramento
Nunca terminar com "continuar analisando" nem com "custo não alocado" tratado como resolvido.
Definir:
- próximo dado;
- próxima pergunta;
- próxima validação (inclusive: enviar para Reconciliation Queue);
- próxima ação;
ou
- encerramento justificado.
