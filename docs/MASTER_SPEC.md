# TRIXLOG Torre de Controle — Especificação Mestre

## 1. Visão
Criar uma central de inteligência operacional e executiva para a TRIXLOG Transportes, uma
transportadora rodoviária de carga fechada (FTL) que já emite CT-e, já lança contas a receber e
a pagar — mas não tem visibilidade de rentabilidade por cliente ou por viagem hoje. A empresa só
importa os relatórios que já exporta; a plataforma faz o resto.

### O produto deve responder
- Qual cliente/rota/viagem é mais e menos rentável?
- Onde a margem está vazando — desconto, custo de terceiro, pedágio, inadimplência?
- Quanto custa não agir?
- Qual a causa mais provável do desvio?
- Quais hipóteses alternativas existem?
- Qual viagem/cliente/transportador deve receber esforço agora?
- Quais 3 ações são possíveis?
- Qual entrega o maior resultado com menor esforço?
- Quem deve agir? Em quanto tempo? Como provar que funcionou?
- Uma cotação nova vale a pena aceitar, dada a margem esperada?

## 2. Escopo de domínio
Cobrir, progressivamente:
- rentabilidade por cliente e por viagem (Fase 1 — o problema mais urgente);
- custo de frete terceiro/frota agregada;
- contas a receber e a pagar, DSO, inadimplência;
- cotação/orçamento de frete (venda ao cliente e compra a terceiro);
- ocorrências operacionais (atraso, avaria, extravio);
- frota e produtividade (própria x agregada);
- fiscal (CFOP, consistência tributária do CT-e);
- comércio exterior — DTA, DI, contêiner, importação/exportação (Fase 2, hoje sem dado real —
  ver `.claude/agents/comex-dta-di.md`).

## 3. Arquitetura de inteligência

### Camada A — Cost Allocation Engine
Antes de qualquer outra análise: reconstrói a chave receita (CT-e) → custo (Contrato de
Transporte) → viagem, em 3 camadas (parse determinístico, heurística, conciliação manual). Ver
`docs/COST_ALLOCATION.md`. Sem esta camada, nenhuma rentabilidade por cliente é confiável.

### Camada B — Detecção
Identifica desvio de margem, concentração de custo, inadimplência, atraso recorrente.

### Camada C — Investigação
Agente Investigador valida o fenômeno e decompõe a causa.

### Camada D — Especialistas
O coordenador chama somente os especialistas relevantes (`config/domain-routing.yaml`).

### Camada E — Contraditório
Agente Provocador tenta derrubar a hipótese antes dela virar recomendação.

### Camada F — Priorização
Compara impacto × esforço × risco × prazo × confiança.

### Camada G — Decisão
Conselheiro Executivo converte análise em fila de decisões.

### Camada H — Soluções e Ações Práticas
Recebe diagnóstico validado e produz contenção, correção estrutural e otimização, cada uma com
ação exata, dono, prazo, custo, impacto, risco, KPI, meta, evidência e contingência.

### Camada I — Cotação/Orçamento
Módulo comercial próprio (`docs/QUOTING_MODULE.md`) — venda ao cliente e compra a terceiro, com
guardrail de margem mínima antes de fechar.

### Camada J — Execução
Transforma decisão aprovada em ação, dono, prazo, meta e evidência.

### Camada K — Aprendizado
Registra previsão, decisão, execução e resultado real — inclusive para calibrar a própria
heurística de alocação de custo (Camada A) com o tempo.

## 4. Tipos de inteligência horizontal

### Onde a TRIXLOG está perdendo margem?
Cruzar CT-e (receita), Contas a Pagar (custo de terceiro), pedágio, inadimplência — por cliente,
rota, transportador.

### Cliente destruidor de valor
Cruzar receita, prazo de pagamento, inadimplência, atraso/ocorrência — quem custa mais do que
paga a mais.

### Transportador terceiro/agregado — risco e custo
Cruzar custo, produtividade, ocorrência, concentração — risco de dependência de poucos agregados,
risco de vínculo empregatício disfarçado.

### Estrutura versus resultado
Antes de recomendar frota própria ou mais pessoal, provar que a capacidade/produtividade atual
(inclusive agregados) já está bem utilizada.

## 5. Definições
- Objetivo: resultado que se pretende alcançar.
- Métrica: variável mensurável relacionada ao objetivo.
- KPI: indicador-chave que demonstra se o objetivo está sendo alcançado.
- Estratégia: ações escolhidas para atingir o objetivo.
Nunca misturar os quatro.

## 6. Regra de prontidão para decisão
Uma recomendação só pode ser marcada `READY_FOR_DECISION` se responder:
1. O desvio é real e material?
2. Onde está concentrado?
3. Qual é a causa provável, com confiança ≥ 70?
4. Quais hipóteses alternativas foram testadas?
5. A rentabilidade envolvida tem custo alocado confirmado (Camada 1, 2 ou 3 de `docs/COST_ALLOCATION.md`),
   ou está marcada explicitamente como parcial/não alocada?
6. O que permanece incerto?
7. Qual a consequência de agir e de não agir?
8. Qual alternativa tem melhor impacto/esforço/risco/prazo?
9. Quem executará e como o resultado será comprovado?
10. Estamos eliminando a causa ou só adicionando estrutura para compensar processo ruim?

## 7. Saída executiva
A resposta final deve ser curta, objetiva, rastreável e acionável. Detalhe técnico fica disponível
sob demanda (ver `prompts/EXECUTIVE_OUTPUT_TEMPLATE.md`).

## 8. Métricas do próprio produto
- % de viagens com custo alocado com confiança alta (Camada 1/2) vs. pendente de conciliação manual (Camada 3);
- valor recuperado / perda evitada;
- tempo entre desvio e decisão;
- % de recomendações executadas;
- acurácia do impacto previsto versus realizado;
- % de causas confirmadas;
- reincidência após correção;
- taxa de conversão de cotação em frete fechado;
- desvio entre margem prevista na cotação e margem real pós-execução.
