# PRP — Módulo de Orçamento/Cotação de Frete — TRIXLOG Transportes

**Status:** especificação de funcionalidade nova, sem base histórica no sistema (processo 100% manual via e-mail hoje). Este documento foi desenhado a partir de conhecimento geral de mercado de frete rodoviário de carga fechada (FTL) no Brasil, **não** de dado real da TRIXLOG. Todo ponto que é premissa de mercado (não fato da empresa) está marcado como **[PREMISSA — validar com Tatiana]**.

---

## 0. Escopo e premissa central

O processo real, hoje: o embarcador dispara e-mail de RFQ (request for quote) para várias transportadoras simultaneamente, cada uma cota, o embarcador escolhe uma. A TRIXLOG está dos dois lados dessa cadeia:

- **Lado venda**: TRIXLOG é uma das cotantes disputando o frete do embarcador.
- **Lado compra**: quando fecha o frete, TRIXLOG frequentemente não roda com frota própria — subcontrata um transportador terceiro/agregado (visto em dado real: pagamentos a "MAIOLINI TRANSPORTES LTDA" e outros sob "Contrato de Transporte" com adiantamento + saldo).

O módulo cobre as duas pontas e a costura entre elas: **quanto custa executar** (compra) determina **quanto posso cobrar com margem** (venda) — e isso precisa estar visível *antes* de aceitar o frete, não depois de rodado.

---

## 1. Entidades do módulo

Campos alinhados à nomenclatura já usada no CT-e real da empresa (frete peso, pedágio, subtotal, total, origem/destino, CFOP, modal) para não criar um vocabulário paralelo.

### 1.1 `SolicitacaoCotacao`
O pedido recebido do cliente (embarcador).

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `cliente_id` | FK → Cliente | se cliente novo, capturar dados mínimos (razão social, CNPJ, contato) |
| `origem_cidade` / `origem_uf` | string | mesma granularidade do "Local de Coleta" do CT-e |
| `destino_cidade` / `destino_uf` | string | mesma granularidade do "Local de Entrega" do CT-e |
| `tipo_carga` | enum | carga geral, granel sólido/líquido, perigosa (ADR), refrigerada, viva, indivisível/especial |
| `peso_kg` | decimal | |
| `cubagem_m3` | decimal | nullable — nem todo pedido informa |
| `valor_mercadoria` | decimal | base para seguro/ad valorem |
| `quantidade_volumes` | int | nullable |
| `tipo_veiculo_solicitado` | enum | truck, carreta, bitrem, rodotrem etc. |
| `data_coleta_desejada` | date | |
| `data_entrega_desejada` | date | nullable |
| `prazo_resposta` | datetime | deadline informado pelo cliente (deadline do RFQ) |
| `canal_origem` | enum | `manual` (MVP), `email_ingestao` (fase 2) |
| `email_origem_raw` | text | nullable — corpo do e-mail original, se veio por ingestão |
| `observacoes` | text | |
| `status` | enum | ver máquina de estados abaixo |
| `created_by` / `created_at` | | |

### 1.2 `Cotacao` (venda — proposta ao cliente)
Pode ter múltiplas revisões dentro da mesma solicitação (negociação de preço/prazo).

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `solicitacao_cotacao_id` | FK | |
| `numero_versao` | int | 1, 2, 3... a cada revisão |
| `valor_frete_peso` | decimal | espelha campo do CT-e |
| `valor_pedagio` | decimal | espelha campo do CT-e |
| `valor_seguro_ad_valorem` | decimal | |
| `valor_gris_outras_taxas` | decimal | taxas de mercado (GRIS, TDE, etc.) — **[PREMISSA — nomenclatura de mercado, validar quais a TRIXLOG realmente cobra]** |
| `valor_subtotal` | decimal | soma dos itens acima |
| `valor_total` | decimal | valor final proposto ao cliente |
| `modal` | enum | rodoviário (fixo, mas mantém o campo por paridade com CT-e) |
| `cfop_previsto` | string | CFOP esperado se essa cotação virar CT-e |
| `prazo_entrega_dias` | int | |
| `validade_proposta` | date | até quando a proposta vale |
| `custo_estimado_execucao` | decimal | **interno, nunca exposto ao cliente** — vem de `CotacaoCompra` vinculada ou de custo médio histórico da rota |
| `margem_valor` / `margem_percentual` | decimal | calculado = (`valor_total` − `custo_estimado_execucao`) / `valor_total` — interno |
| `status` | enum | ver máquina de estados |
| `motivo_perda` | enum/text | nullable — preenchido se recusada (preço, prazo, concorrente, etc.) |
| `cte_id` | FK nullable | preenchido quando a cotação vira frete real |
| `sent_at` / `responded_at` | datetime | |

### 1.3 `CotacaoCompra` (compra — cotação a terceiro/agregado)

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `cotacao_id` | FK → `Cotacao` | a qual cotação de venda essa compra está amarrada |
| `transportador_terceiro_id` | FK → `Parceiro`/`MotoristaAgregado` | cadastro de terceiros (ex.: MAIOLINI TRANSPORTES) |
| `valor_frete_negociado` | decimal | |
| `percentual_adiantamento` | decimal | % pago adiantado — padrão de mercado do frete agregado |
| `valor_adiantamento` | decimal | |
| `valor_saldo` | decimal | |
| `forma_pagamento` | enum | PIX, boleto, etc. |
| `prazo_pagamento_saldo` | int (dias) | |
| `veiculo_placa` / `motorista_nome` | string | nullable até confirmação |
| `status` | enum | ver máquina de estados |
| `contrato_transporte_id` | FK nullable | vínculo com o documento "Contrato de Transporte" já usado na operação real |
| `data_solicitacao` / `data_resposta` | datetime | |

### 1.4 Relação entre entidades

```
SolicitacaoCotacao (1) ──< (N) Cotacao [revisões/versões]
Cotacao (1) ──< (N) CotacaoCompra [pode consultar N terceiros para a mesma venda]
CotacaoCompra (N) ──> (1) Cotacao selecionada como "vencedora" no lado compra
Cotacao (1) ──── (0..1) CTe  [conversão final]
CotacaoCompra confirmada (1) ──── (0..1) ContratoTransporte
```

Regra de integridade: uma `Cotacao` só pode ir para `convertida_cte` se tiver **ao menos uma referência de custo** — seja uma `CotacaoCompra` confirmada, seja um custo médio histórico assumido explicitamente (campo `custo_estimado_execucao` não pode ficar nulo/zero nesse ponto). Isso é o que impede repetir o problema de "descobrir a rentabilidade só depois que já rodou".

---

## 2. Máquina de estados

### 2.1 `Cotacao` (venda)

```
rascunho
  └─(usuário envia)──> enviada_cliente
enviada_cliente
  ├─(cliente contrapropõe / pede ajuste — registro manual)──> em_negociacao
  ├─(cliente aceita — registro manual, e-mail de aceite)──> aprovada_cliente
  ├─(validade_proposta expira sem resposta — job agendado)──> expirada
  └─(cliente recusa explicitamente)──> recusada_cliente
em_negociacao
  └─(nova revisão gerada, numero_versao++)──> enviada_cliente
aprovada_cliente
  └─(CT-e emitido referenciando esta cotação — automático pelo módulo de CT-e)──> convertida_cte
rascunho
  └─(usuário cancela antes de enviar)──> cancelada
```

Gatilhos e responsáveis:
- `rascunho → enviada_cliente`: ação humana (MVP) ou agente com confirmação humana (fase 2).
- `enviada_cliente → em_negociacao / aprovada_cliente / recusada_cliente`: **sempre registro manual** — a resposta do cliente chega por e-mail fora do sistema no MVP.
- `enviada_cliente → expirada`: job agendado, automático, sem intervenção humana.
- `aprovada_cliente → convertida_cte`: automático, disparado pelo sistema de emissão de CT-e quando um CT-e referencia o `cotacao_id`. **Bloqueado** se a cotação estiver abaixo da margem mínima sem aprovação registrada (ver seção 4).

### 2.2 `CotacaoCompra` (compra a terceiro)

```
rascunho
  └─(usuário dispara para N terceiros)──> solicitada
solicitada (por terceiro, sub-status individual: enviada/respondida/recusada/sem_resposta)
  └─(ao menos 1 resposta registrada)──> respostas_recebidas
respostas_recebidas
  └─(usuário escolhe 1 entre as N)──> selecionada
selecionada
  └─(contrato de transporte gerado, adiantamento definido)──> confirmada
solicitada
  └─(nenhum terceiro respondeu até prazo)──> sem_resposta (necessita nova rodada)
```

Gatilhos: solicitação e seleção são sempre ação humana no MVP (mesma lógica do processo real hoje — negociação por telefone/WhatsApp/e-mail com o agregado). `confirmada` trava o `custo_estimado_execucao` da `Cotacao` de venda vinculada.

---

## 3. Cálculo de preço de venda (frete ao cliente)

### 3.1 O que é determinístico

1. **Tabela de referência por rota** (praça origem × praça destino, ou faixa de km se não houver rota cadastrada) com valor-base por eixo/tipo de veículo. Fonte inicial: nenhuma — precisa ser populada manualmente pela Tatiana/equipe comercial no MVP. **[PREMISSA — não existe hoje uma tabela formal na TRIXLOG, é premissa de que uma tabela assim precisa existir; validar]**.
2. **Custo médio histórico da rota**: se já existem CT-e's emitidos na mesma rota (ou rota similar por par de UF), o sistema pode calcular `custo_médio = média(frete_peso + pedágio)` dos últimos N fretes executados naquela rota. Isso é dado real e pode ser aprendido do histórico de CT-e — diferente da tabela de referência, que é premissa de mercado.
3. **Piso legal ANTT**: a Lei 13.703/2018 instituiu política de preços mínimos para o transporte rodoviário de cargas, operacionalizada pela ANTT via tabelas de piso por eixo/tipo de carga. **Cito isso como referência de piso legal, não como fórmula de precificação** — a aplicabilidade exata (se cobre contratação de transportadora-a-transportadora como no caso da CotacaoCompra, ou só contratação direta de autônomo/TAC) e a validade jurídica de exigibilidade têm sido objeto de disputa judicial ao longo dos anos. **[PREMISSA — validar com jurídico/Tatiana se e como esse piso se aplica à operação da TRIXLOG antes de usar como guardrail automático de bloqueio]**.
4. **Margem desejada configurável**: `valor_proposto = custo_estimado / (1 − margem_alvo%)`, com `margem_alvo%` parametrizável por segmento de cliente ou tipo de carga.
5. **Prioridade de fonte de custo**: `CotacaoCompra` confirmada > custo médio histórico da rota (CT-e reais) > tabela de referência por km/praça (fallback quando não há nenhum dado). O sistema deve expor visivelmente qual fonte foi usada — isso é dado de confiança da estimativa, não só o número final.

### 3.2 O que precisa de julgamento humano ou de agente de IA opinando

Não modelar como fórmula fixa — são ajustes contextuais:
- **Sazonalidade** (safra, pico de demanda, escassez de caminhão em determinada praça/época).
- **Relacionamento com o cliente** (cliente estratégico, volume recorrente, histórico de pagamento) — pode justificar margem menor conscientemente, não por erro.
- **Urgência do embarcador** (coleta em cima da hora tende a custar mais, tanto no lado compra quanto no preço de venda).
- **Intensidade da concorrência percebida** (quantas outras transportadoras o cliente mencionou estar cotando, se souber).
- **Risco da carga** (valor alto, perecível, perigosa) — pode exigir ajuste de seguro/ad valorem além do cálculo padrão.

Esses fatores devem aparecer como **campos de ajuste explícitos e auditáveis** na `Cotacao` (ex.: `ajuste_manual_percentual`, `justificativa_ajuste`), nunca embutidos silenciosamente no número — para não virar uma caixa-preta que ninguém sabe por que cotou o que cotou.

---

## 4. Por que isso é decisão, não calculadora — guardrail de margem

Toda `Cotacao` que muda para `enviada_cliente` ou tenta ir para `convertida_cte` deve expor **margem esperada calculada** (`margem_percentual`) antes da ação, não depois do frete rodado.

**Regra de negócio explícita — "cotação abaixo da margem mínima aceitável":**

- `margem_minima_aceitavel` é um parâmetro configurável (global ou por segmento de cliente/rota). **[PREMISSA de mercado — proponho algo na faixa de 8–15% para FTL rodoviário como ponto de partida, mas isso precisa ser validado com a Tatiana com base na realidade de custo da TRIXLOG, não é número de mercado universal]**.
- Se `margem_percentual` calculada < `margem_minima_aceitavel`:
  - O sistema **não bloqueia a cotação de ser enviada ao cliente** (o comercial pode negociar preço), mas **bloqueia a transição para `convertida_cte`** sem uma aprovação explícita.
  - Aprovação obrigatória: um usuário com papel de gestor precisa registrar `aprovacao_margem_baixa` com `aprovado_por`, `justificativa`, `timestamp` antes que o CT-e possa ser gerado a partir dessa cotação.
  - Isso vale **mesmo que o cliente já tenha aceitado o preço** — a aceitação do cliente resolve o lado comercial, não o lado de rentabilidade interna. São duas aprovações distintas.
- Toda `CotacaoCompra` confirmada que reduza a margem da `Cotacao` de venda já enviada/aprovada abaixo do mínimo deve reabrir o mesmo alerta antes de `confirmada` — o custo de execução pode mudar depois que o preço já foi prometido ao cliente.
- Log de auditoria obrigatório para todo override — é o mesmo padrão do resto da plataforma: decisão de negócio registrada, não escondida dentro de um cálculo automático.

---

## 5. Integração de e-mail — MVP vs. fases futuras

**Regra de governança inegociável, válida em todas as fases:** o sistema nunca responde automaticamente ao cliente com preço ou compromisso comercial sem revisão humana. Preço cotado é compromisso comercial real; erro aqui tem custo direto e reputacional.

| Fase | Escopo | Automação | Humano no loop |
|---|---|---|---|
| **MVP** | Usuário cadastra manualmente a `SolicitacaoCotacao` na plataforma a partir do e-mail recebido. Envio da proposta ao cliente continua manual (fora do sistema ou via cópia do texto gerado). | Nenhuma automação de e-mail. | 100% — cadastro, envio e registro de resposta são manuais. |
| **Fase 2** | Um agente lê e-mails de pedido de cotação recebidos e **pré-preenche** a `SolicitacaoCotacao` (origem, destino, peso, tipo de carga, prazo). | Ingestão semiautomática. | Humano confirma/corrige os campos pré-preenchidos antes que a solicitação entre no fluxo de cotação. Nenhum e-mail sai automaticamente nessa fase. |
| **Fase 3 (fora do escopo deste PRP, só como direção futura)** | Agente pode **rascunhar** a resposta de cotação (usando o Email Agent oficial da SAL, não um mecanismo de envio próprio, se for esse o caminho adotado pela organização). | Rascunho automático. | Envio permanece sempre com aprovação humana explícita antes do disparo — nunca envio automático de preço. |

---

## 6. Métricas do módulo

Objetivo: o módulo não serve só para cotar, serve para a empresa aprender com o tempo se está cotando certo — o mesmo conceito de aprendizado organizacional usado no resto da plataforma.

| Métrica | Cálculo | Para que serve |
|---|---|---|
| Taxa de conversão | `cotações convertidas_cte` / `cotações enviadas_cliente` | saúde comercial do funil |
| Tempo médio de resposta | `sent_at` − `SolicitacaoCotacao.created_at` | velocidade de resposta vs. concorrência (cliente manda pra várias ao mesmo tempo — quem responde rápido tem vantagem) |
| Motivo de perda (distribuição) | agregação de `motivo_perda` | preço vs. prazo vs. outro — calibra estratégia |
| Margem média prevista (aprovadas) | média de `margem_percentual` no momento da conversão | referência de precificação planejada |
| Margem real pós-execução | recalculada com custos reais do CT-e + `CotacaoCompra` efetivamente paga (incluindo eventuais desvios de adiantamento/saldo) | compara previsto vs. realizado |
| Desvio de margem (previsto vs. realizado) | `margem_real − margem_prevista` | **o número mais importante do módulo** — alimenta recalibração da tabela de referência e dos parâmetros de margem mínima ao longo do tempo |
| Número médio de revisões por cotação | `max(numero_versao)` por solicitação | indica o quanto cada negociação está "brigada" |
| Fill rate por rota | `solicitações que viraram CT-e` / `solicitações recebidas`, por rota | onde a TRIXLOG converte bem vs. onde está perdendo sistematicamente |
| Desvio custo estimado vs. custo real de terceiro | comparação `custo_estimado_execucao` vs. `valor_frete_negociado` real na `CotacaoCompra` | calibra a fonte de custo usada (tabela vs. histórico) |

O desvio de margem previsto vs. realizado deve alimentar uma rotina periódica (mensal, por exemplo) de recalibração dos parâmetros de precificação — **com revisão humana**, não ajuste automático silencioso, para não deixar o modelo derivar sem supervisão.

---

## Resumo de premissas a validar com a Tatiana

1. Existência/necessidade de uma tabela de referência de frete por rota — hoje não existe formalizada.
2. Quais taxas acessórias a TRIXLOG realmente cobra (GRIS, TDE, ad valorem, etc.) e seus nomes exatos.
3. Faixa de margem mínima aceitável (sugestão de 8–15% é ponto de partida genérico de mercado, não número real da empresa).
4. Aplicabilidade do piso mínimo ANTT (Lei 13.703/2018) à operação específica da TRIXLOG, especialmente no lado da subcontratação a terceiros/agregados.
5. Percentual padrão de adiantamento pago a transportadores terceiros/agregados (visto em dado real como prática, mas percentual e regras precisam confirmação).
6. Se e quando a organização quer avançar para a Fase 3 (rascunho automático de resposta via Email Agent) — este PRP não recomenda isso para o MVP nem Fase 2.
