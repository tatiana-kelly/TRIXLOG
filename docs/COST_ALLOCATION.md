# PRP — Modelo Financeiro e Lógica de Alocação de Custo
## TRIXLOG Transportes — Torre de Controle FTL

---

## 0. Cobertura real medida (Fase 0, `backend/scripts/run_real_import.py` contra os 3 arquivos completos)

- Importação: 67/68 CT-e, 45/46 Contas a Receber, 78/79 Contas a Pagar (1 linha rejeitada em
  cada por falta de campo obrigatório — coerente entre os três).
- Camada 1 (Fatura → CT-e via Observação): 45/45 faturas importadas têm ao menos 1 Conhecimento
  referenciado. 69 referências no total, 4 sem CT-e correspondente no arquivo (provavelmente
  fora do período exportado).
- Contas a Pagar por tipo real: 20 `contrato_transporte`, 57 `nota_entrada`, 1
  `antecipacao_recebiveis` — nenhuma linha caiu em "outro" (o parser cobre 100% do formato real).
- 12 `ContratoTransporte` reconstruídos.
- **Camada 2 (heurística nome+data, com trava de 1 contrato = 1 CT-e): 3/67 CT-e's (4,5%)
  vinculados automaticamente. 95,5% caem para a Camada 3 (conciliação manual).** Isso é mais
  pessimista ainda que o achado de "2/79 coincidências numéricas" de uma auditoria independente
  — e é o número certo, não uma estimativa: a primeira versão da heurística permitia que o mesmo
  contrato fosse "encontrado" por vários CT-e's do mesmo transportador na mesma janela, inflando
  o custo alocado (ex.: LOJAS EDMIL S/A chegou a mostrar custo_alocado 4x maior que a receita)
  até a trava de reivindicação única ser adicionada. **Conclusão prática: a fila de conciliação
  manual (Camada 3) não é um fallback raro — é o caminho principal. Investir ali, não em deixar
  a heurística "mais esperta".**

### 0a. Cobertura real medida contra os 337 CT-e's do trimestre completo (mai/jun/jul, matriz+filial), depois da Camada 0 (Carta Frete)

- **Antes da Camada 0 (só Camada 1+2): 45/337 = 13,4%.**
- **Depois da Camada 0 (join 1:1 apenas): 106/337 = 31,5%.** Camada 0 resolveu 94 CT-e's (join
  direto e determinístico com `CartaFrete` via `(CTRC, unidade)`, ver seção 10a); Camada 2
  (heurística, rodando só sobre o que sobrou) resolveu mais 12.
- **Depois de tratar CTRC multi-valor com rateio proporcional (seção 10a): 122/337 = 36,2%.**
  Achado real: 2 cartas-frete cobrem várias viagens numa linha só (`CTRC="371,374,376,377,380"`,
  `CTRC` com 13 números) — 18 CT-e's a mais resolvidos via rateio por participação de receita
  (`carta_frete_rateado`, confiança 0,8, distinto do link direto). Também achado e tratado: 1
  CT-e (309/filial) reivindicado por DUAS cartas-frete diferentes na origem — nenhuma das duas
  linka automaticamente, cai para conciliação manual (nunca escolher arbitrariamente).
- Resultado real na tela "Rentabilidade por cliente" (julho/2026): viagens com custo alocado
  subiu de 15 (antes de qualquer Camada 0) para 52; margem confirmada do mês foi de
  -R$ 38.652,17 para um valor bem menos negativo — ainda negativa (fato real, não erro), mas com
  bem menos viagens "não determinável" escondendo o tamanho real do problema.
- 215 CT-e's (63,8%) ainda pendentes — a maioria é frota própria (sem chave de custo direto
  ainda, ver seção 10) e frete terceiro sem Carta Frete nem contrato correspondente nos
  relatórios recebidos até agora.

---

## 1. Modelo de Dados Canônico Proposto

### 1.1 Entidade: `CTe` (Receita — fonte: **CT-e.xlsx**, 68 linhas)

Representa o documento fiscal de frete. É a unidade atômica de receita.

| Campo canônico | Tipo | Coluna de origem (planilha real) |
|---|---|---|
| `cte_tipo` | string/enum | Tipo (CT-e ou "67") |
| `cte_numero` | string (manter zero à esquerda) | Número |
| `cte_serie` | string | Série |
| `data_emissao` | date | Data de Emissão |
| `local_coleta` | string | Local de Coleta |
| `local_entrega` | string | Local de Entrega |
| `cfop` | string | CFOP |
| `pagador_frete_nome` | string | Pagador do Frete - Nome |
| `remetente_nome` | string | Remetente - Nome |
| `remetente_endereco` | string | Remetente - Endereço |
| `remetente_cidade` | string | Remetente - Cidade |
| `remetente_cnpj` | string (texto, não float) | Remetente - CNPJ |
| `destinatario_nome` | string | Destinatário - Nome |
| `destinatario_endereco` | string | Destinatário - Endereço |
| `destinatario_cidade` | string | Destinatário - Cidade |
| `destinatario_cnpj` | string (texto) | Destinatário - CNPJ |
| `proprietario_veiculo_nome` | string | Proprietário do Veículo - Nome |
| `veiculo_placa` | string | Veículo - Placa |
| `motorista_nome` | string | Motorista - Nome |
| `valor_frete` | decimal | Valor do Frete |
| `valor_frete_peso` | decimal | Valor do Frete Peso |
| `pedagio` | decimal | Pedágio |
| `subtotal` | decimal | Subtotal |
| `total` | decimal | Total |
| `modal` | string | Modal (observado sempre "Rodoviário") |
| `data_entrega` | date | Data de Entrega |
| `ultima_ocorrencia` | string | Última Ocorrência |

**Chave primária:** `(cte_numero, cte_serie)`.
**Cliente pagador de fato:** `Pagador do Frete - Nome` — não necessariamente igual a Remetente ou Destinatário. **É esta a coluna que define "cliente" para fins de rentabilidade**, não `Contas Receber.Cliente` isoladamente (ver seção 4).

### 1.2 Entidade: `FaturaReceber` (fonte: **Contas Receber.xlsx**, 46 linhas)

Representa uma cobrança ao cliente, que pode consolidar **N** CT-e's.

| Campo canônico | Tipo | Coluna de origem |
|---|---|---|
| `fatura_id` | string (gerar surrogate key — não há Número de Fatura explícito nas colunas listadas) | — (PREMISSA A VALIDAR: confirmar se existe coluna de nº de fatura não citada) |
| `cliente_nome` | string | Cliente |
| `centro_receita` | string | Centro de Receita (valor visto: "FRETE - CTE") |
| `valor_total` | decimal | Valor Total |
| `dt_vencimento` | date | Dt. Vencimento |
| `baixado` | boolean (Sim/Não) | Baixado |
| `dt_pagamento` | date, nullable | Dt. Pagamento |
| `valor_pago` | decimal, nullable | Valor Pago |
| `tipo_pagamento` | enum (PIX, Boleto Bancário) | Tipo de Pagamento |
| `observacao_raw` | text | Observação |
| `ctes_referenciados[]` | array de `cte_numero` | **derivado** via parse de `observacao_raw` (Camada 1, seção 2) |

### 1.3 Entidade: `PagamentoFornecedor` (fonte: **Contas Pagar.xlsx**, 79 linhas)

Representa uma saída de caixa — pode ser frete terceirizado/agregado OU despesa operacional (combustível, insumo).

| Campo canônico | Tipo | Coluna de origem |
|---|---|---|
| `pagamento_id` | surrogate key | — |
| `fornecedor_nome` | string | Fornecedor |
| `centro_custo` | string, nullable | Centro de Custo (valor visto: "FRETES TERCEIROS"; **NaN** para outras despesas) |
| `valor` | decimal | Valor |
| `favorecido_nome` | string, nullable | Favorecido - Nome |
| `favorecido_cnpj` | string, nullable | Favorecido - CNPJ |
| `favorecido_banco` | string, nullable | Favorecido - Banco |
| `favorecido_agencia` | string, nullable | Favorecido - Agência |
| `favorecido_conta` | string, nullable | Favorecido - Conta |
| `favorecido_pix` | string, nullable | Favorecido - Pix |
| `observacao_raw` | text | Observação |
| `contrato_transporte_numero` | int, nullable | **derivado** via parse de `observacao_raw` (regex "Contrato de Transporte número NN") |
| `tipo_parcela` | enum (Adiantamento, Saldo, Outro) | **derivado** via parse de `observacao_raw` |

**Nota crítica:** só é custo de frete direto (imputável a uma viagem) quando `centro_custo = "FRETES TERCEIROS"` **e** `observacao_raw` contém referência a "Contrato de Transporte". Combustível de frota própria e outras despesas com `centro_custo = NaN` são custos operacionais **não diretamente ligados a um CT-e específico** neste export — ver Camada 2/DRE.

### 1.4 Entidade inferida: `ContratoTransporte`

Não existe como planilha própria — é reconstruída a partir de `PagamentoFornecedor.observacao_raw`. Cada contrato gera **2 registros de pagamento** (Adiantamento + Saldo), confirmado pelo padrão real: "Pagamento ref. ao Documento de Adiantamento de Carta Frete do Contrato de Transporte número 68;" seguido depois de "...Saldo do Contrato de Transporte número 68;".

| Campo canônico | Tipo | Origem |
|---|---|---|
| `contrato_numero` | int | extraído de Observação |
| `valor_adiantamento` | decimal | soma dos pagamentos com `tipo_parcela=Adiantamento` para esse contrato |
| `valor_saldo` | decimal | soma dos pagamentos com `tipo_parcela=Saldo` |
| `valor_total_contrato` | decimal | adiantamento + saldo |
| `fornecedor_nome` | string | herdado de `PagamentoFornecedor.fornecedor_nome` (deve ser o mesmo nos 2 registros — se não for, é sinal de dado inconsistente) |

**Este contrato é o custo de frete terceiro por viagem — mas não tem, nestes exports, nenhuma FK direta para `cte_numero`.** Essa é a lacuna central do problema.

### 1.5 Entidade central a construir: `Viagem` (Trip)

Não existe fonte primária — é o resultado do processo de conciliação (seção 2). Estrutura alvo:

| Campo | Origem |
|---|---|
| `viagem_id` | surrogate key |
| `cte_numero` (1 ou N) | CTe |
| `contrato_transporte_numero` (0, 1 ou N) | ContratoTransporte |
| `metodo_vinculo` | enum: `regex_observacao` \| `heuristica_placa_data` \| `manual` \| `nao_vinculado` |
| `confianca_vinculo` | 0.0–1.0 |
| `receita_total` | soma de `CTe.total` dos CT-e's vinculados |
| `custo_frete_terceiro` | `ContratoTransporte.valor_total_contrato` vinculado (se houver) |
| `margem_contribuicao_bruta` | receita_total − custo_frete_terceiro |

---

## 2. Estratégia de Alocação de Custo → Receita → Cliente

### Camada 1 — Parse determinístico de Observação (regex)

**Contas Pagar.Observação:** extrair `Contrato de Transporte número (\d+)` e classificar `Adiantamento` vs `Saldo` pela presença das palavras "Adiantamento"/"Saldo" na mesma string.

**Contas Receber.Observação:** extrair todos os `Conhecimento (\d+)` — já confirmado que o campo suporta múltiplos números na mesma fatura (ex.: "Fatura ref. aos Conhecimentos 000377, 000380, 000382;").

**O que essa camada resolve:** vincula `FaturaReceber → CTe` (1 fatura → N CT-e's) com alta confiança, porque o padrão textual é regular e as duas amostras citadas seguem exatamente esse formato.

**O que essa camada NÃO resolve — o gap central:** ela não vincula `CTe.cte_numero` a `ContratoTransporte.contrato_transporte_numero`, porque **são duas séries numéricas independentes** (contratos vistos: 68, 69; CT-e's vistos: 24, 382, 384, 385, 386 — sem sobreposição nem relação aritmética aparente). O regex, sozinho, resolve a ponte Fatura→CT-e (lado receita) e a ponte Pagamento→Contrato (lado custo), mas **não fecha o elo CT-e↔Contrato**, que é exatamente o que falta para calcular margem por viagem.

**Taxa de cobertura esperada (PREMISSA A VALIDAR, sem acesso aos dados brutos completos):**
- Fatura → CT-e: alta (regex simples, formato consistente nos 2 exemplos vistos) — mas depende de 100% das 46 linhas seguirem o padrão "Fatura ref. ao(s) Conhecimento(s) NNNNNN". Qualquer variação de wording (abreviação, erro de digitação, campo em branco) quebra o match.
- Pagamento → Contrato: idem, alta para os registros com `Centro de Custo = "FRETES TERCEIROS"`. Mas há linhas com `Centro de Custo = NaN` (combustível, insumo) que **não têm e não devem ter** contrato de transporte — essas ficam corretamente fora do escopo de custo direto por viagem.
- Casos que a Camada 1 não resolve: (a) Observação vazia/nula; (b) Observação com texto livre fora do padrão esperado; (c) um Contrato de Transporte que never aparece referenciado a nenhum CT-e — porque a chave simplesmente não existe nesse texto.

### Camada 2 — Heurística automática (fallback)

Quando a Camada 1 não fecha o elo `CTe ↔ ContratoTransporte`, aplicar heurística por similaridade de atributos:

- **Match candidato:** mesma janela de datas — **corrigido após inspeção da planilha completa**:
  Contas Pagar TEM campos de data (`Dt. Emissão`, `Dt. Movimento`, `Dt. Vencimento`, `Dt. Pagamento`,
  `Dt. Lançamento`), ao contrário do que uma leitura por amostra pequena sugeriu antes — usar
  `Dt. Emissão` do pagamento vs. `Data de Emissão` do CT-e, janela de poucos dias **+** mesmo
  `fornecedor_nome`/`favorecido_nome` aproximando-se do `motorista_nome` ou `proprietario_veiculo_nome`
  do CT-e (fuzzy match de nome, já que motorista PF pode aparecer com grafia distinta em cada sistema).
- **Achado empírico (auditoria independente rodada contra os 3 arquivos completos):** apenas
  **2 de 79 linhas de Contas a Pagar** apresentaram coincidência numérica segura com um CT-e.
  Ou seja, a Camada 2 deve ser tratada como **raramente decisiva na prática**, não como fallback
  intermediário robusto — a maioria dos casos vai cair direto na Camada 3 (conciliação manual).
  Dimensionar o esforço de engenharia de acordo: investir mais na qualidade da fila de conciliação
  manual (Camada 3) do que em sofisticar a heurística automática.
- **Confiabilidade: baixa a média.** Nomes de motorista/transportador podem se repetir para vários CT-e's na mesma semana (um motorista roda várias cargas), então "mesmo fornecedor + mesma janela de data" pode gerar **match ambíguo N:N**, não 1:1. Placa de veículo (`Veículo - Placa` no CT-e) seria o sinal mais forte, mas não existe campo de placa em Contas Pagar — então essa heurística exige nome como proxy, que é o campo mais sujeito a erro de digitação/variação (ex. "MAIOLINI TRANSPORTES LTDA" vs. nome do motorista pessoa física dirigindo para esse mesmo proprietário).
- Regra de negócio: só aceitar automaticamente um match de Camada 2 se houver exatamente 1 candidato dentro da janela (data + nome). Se houver mais de 1 candidato, cai para Camada 3 obrigatoriamente — nunca decidir automaticamente em caso de ambiguidade.

### Camada 3 — Fila de conciliação manual

Para tudo que sobrar sem match de Camada 1 (alta confiança) nem match único de Camada 2:

**Tela de decisão (não dashboard):**
- Lista de "Viagens pendentes de vínculo", uma por linha: CT-e (número, cliente pagador, data, valor, motorista/placa do CT-e).
- Ao abrir um item: painel lateral com os N candidatos de `ContratoTransporte` mais prováveis, ordenados por score da Camada 2 (mesmo fornecedor, data próxima), mostrando fornecedor, valor do contrato, data do pagamento.
- Operador escolhe: (a) vincular a um dos candidatos sugeridos; (b) buscar manualmente por outro número de contrato; (c) marcar como "sem custo de terceiro identificável" (ex.: viagem com veículo próprio, sem frete terceirizado — aí o custo é só combustível/operacional, tratado na DRE geral, não por viagem).
- Cada decisão grava: `viagem_id`, `metodo_vinculo=manual`, `confianca_vinculo=1.0` (decisão humana), e os atributos que levaram à decisão (nome usado, proximidade de data) — **esse log é o dataset de treino/ajuste de peso da Camada 2** (ex.: se toda vez que o operador escolhe o candidato #1 sugerido, aumenta a confiança daquele critério; se o operador sistematicamente ignora sugestões por nome de motorista e prioriza por valor de contrato, o sistema deveria reponderar).

**Recomendação explícita a pedir à Tatiana/TRIXLOG:** solicitar ao sistema de origem (TMS, aparenta ser um sistema padrão do mercado de FTL brasileiro que gera numeração de CT-e e de Contrato de Transporte separadamente — comum em ERPs de transporte no Brasil) um relatório de **Viagem / Manifesto de Carga / Romaneio / Ordem de Serviço**, que internamente já deve ligar as duas séries. Colunas esperadas nesse relatório ideal:
- Número da Viagem/OS/Manifesto
- Número(s) de CT-e vinculados a essa viagem
- Número do Contrato de Transporte (Carta Frete) vinculado
- Placa do veículo e motorista
- Data de início/fim da viagem
- Valor de frete cobrado (deveria bater com o CT-e) e valor de frete pago ao terceiro (deveria bater com o Contrato de Transporte)

Isso eliminaria as Camadas 2 e 3 quase por completo, transformando-as em uma auditoria de exceção em vez do fluxo principal.

---

## 3. DRE Gerencial da Transportadora

Estrutura construída **apenas** com o que os 3 relatórios contêm hoje, em duas camadas: por viagem (contribuição) e da empresa (EBITDA).

### 3.1 Por viagem/CT-e (Margem de Contribuição)

```
  Receita de Frete                         = CTe.Valor do Frete + CTe.Valor do Frete Peso
                                              (ou simplesmente CTe.Total, a validar qual é
                                              o total líquido de pedágio)
(–) Pedágio                                = CTe.Pedágio
                                              [PREMISSA A VALIDAR: confirmar se Pedágio já
                                               está incluso em Total/Subtotal ou é repasse
                                               puro sem margem]
(–) Frete pago a terceiro/agregado          = ContratoTransporte.valor_total_contrato
                                              (vinculado via Camada 1/2/3)
                                              — SÓ aplicável quando a viagem foi operada
                                              por terceiro (Centro de Custo = "FRETES
                                              TERCEIROS"); se veículo é frota própria,
                                              esta linha é 0 e o custo vai para combustível
                                              geral (não alocável por viagem nestes dados)
(–) Combustível direto (quando alocável)    = NÃO EXISTE campo de combustível por viagem
                                              nestes 3 exports — Contas Pagar traz
                                              combustível como despesa de fornecedor
                                              (ex. "REDE DOM PEDRO DE POSTOS LTDA") com
                                              Centro de Custo = NaN, sem vínculo a CT-e.
                                              PREMISSA A VALIDAR: só alocável por viagem
                                              se houver relatório de abastecimento por
                                              viagem/veículo/placa+data.
= Margem de Contribuição por Viagem
```

### 3.2 Consolidado da empresa (rumo a EBITDA)

```
  Receita Bruta de Frete                    = Σ CTe.Total (ou Σ FaturaReceber.Valor Total,
                                               que deveria reconciliar 1:1 se toda receita
                                               vira fatura — validar diferença entre os
                                               dois totais como controle de integridade)
(–) Frete pago a terceiros (todos)          = Σ PagamentoFornecedor.Valor onde
                                               Centro de Custo = "FRETES TERCEIROS"
(–) Pedágio                                 = Σ CTe.Pedágio
= Margem de Contribuição Total (Frete)

(–) Combustível e insumos operacionais      = Σ PagamentoFornecedor.Valor onde
                                               Centro de Custo = NaN e Fornecedor é
                                               claramente insumo operacional (ex. posto de
                                               combustível) — requer classificação manual
                                               inicial dos fornecedores sem Centro de Custo,
                                               pois hoje esse campo não distingue tipo de
                                               despesa
(–) Outras despesas administrativas/fixas   = PREMISSA A VALIDAR — folha de pagamento,
    (folha, aluguel, seguros, manutenção      aluguel, IPVA/seguro de frota, manutenção,
     de frota, etc.)                          pró-labore etc. NÃO estão presentes em
                                               nenhuma das 3 planilhas fornecidas. Precisam
                                               de uma quarta fonte (ex. plano de contas
                                               contábil / DRE contábil já existente da
                                               empresa) para fechar o EBITDA.
= EBITDA
```

**Ponto de atenção para reconciliação:** comparar `Σ CTe.Total` com `Σ FaturaReceber.Valor Total` é um teste de integridade natural — se não baterem, há CT-e's não faturados ou faturas sem CT-e correspondente, o que por si só já é um KPI de controle (ver seção 5).

---

## 4. Rentabilidade por Cliente

### 4.1 Fórmula

```
Rentabilidade_Cliente(c) = Σ [ Receita_CTe(cte) − Custo_Frete_Alocado(cte) − Pedágio(cte) ]
                            para todo cte onde CTe.Pagador do Frete - Nome = c
```

Onde:
- `Receita_CTe(cte) = CTe.Total`
- `Custo_Frete_Alocado(cte)` = a parcela do `ContratoTransporte.valor_total_contrato` atribuída àquele CT-e específico (ver 4.2 para o caso de rateio).
- Cliente é definido por `Pagador do Frete - Nome`, **não** por Remetente nem Destinatário (podem ser empresas diferentes do pagador — comum em frete CIF/FOB com intermediários) e **não** diretamente por `Contas Receber.Cliente` sem cruzar — embora na prática devam coincidir, `Contas Receber.Cliente` é o nome usado na fatura consolidada, então deve ser usado para **conciliar**, e `CTe.Pagador do Frete - Nome` para **atribuir por viagem**.

### 4.2 Tratamento de fatura com múltiplos CT-e's

Caso real confirmado: uma fatura referencia vários Conhecimentos (ex. "Conhecimentos 000377, 000380, 000382"). Regra:

- **Se todos os CT-e's da fatura têm o mesmo `Pagador do Frete - Nome`** (caso esperado, já que é uma fatura de um cliente): não há rateio a fazer — cada CT-e mantém sua própria receita e custo individuais, e a fatura serve apenas para o controle de recebimento (Camada AR), não para o cálculo de rentabilidade (que é feito no nível de CT-e/viagem, não de fatura).
- **Se (caso anômalo) uma fatura misturar CT-e's de pagadores diferentes:** tratar como erro de dado a ser sinalizado — uma fatura de Contas Receber está ligada a um `Cliente`, então CT-e's de outro pagador nela referenciados indicam inconsistência de cadastro, não devem ser ratados automaticamente; encaminhar para a fila de conciliação manual (Camada 3, seção 2) como uma anomalia (não como um vínculo custo↔receita).
- **Custo (Contrato de Transporte) vinculado a mais de um CT-e:** se a Camada 2/3 apurar que um único `ContratoTransporte` (um motorista/carreta) transportou carga de mais de um CT-e na mesma viagem (ex. carga fracionada consolidada — atípico para FTL, mas possível), o custo deve ser **rateado proporcionalmente ao peso/valor de frete de cada CT-e** dentro daquele contrato: `Custo_Frete_Alocado(cte) = ContratoTransporte.valor_total_contrato × (CTe.Total / Σ CTe.Total dos CT-e's daquele contrato)`. PREMISSA A VALIDAR: como FTL (carga fechada) tipicamente é 1 contrato = 1 CT-e = 1 caminhão, este caso deve ser raro; a regra existe como salvaguarda, não como fluxo principal.

---

## 5. Métricas/KPIs Calculáveis Hoje (sem dado novo)

Todos abaixo usam exclusivamente colunas já confirmadas nas 3 planilhas:

| KPI | Fórmula / fonte |
|---|---|
| Ticket médio de frete por cliente | Média de `CTe.Total` agrupado por `Pagador do Frete - Nome` |
| Receita total por cliente | Soma de `CTe.Total` por `Pagador do Frete - Nome` |
| % de CT-e's com ocorrência de atraso | Contagem de `CTe.Última Ocorrência` cujo texto indica atraso, sobre total de CT-e's — **PREMISSA A VALIDAR**: os valores possíveis desse campo não foram integralmente enumerados; assumir que contém strings como "Em Atraso"/"Entregue" a confirmar com amostra completa |
| Prazo médio de entrega | `Data de Entrega − Data de Emissão` (dias), média geral e por cliente |
| DSO (prazo médio de recebimento) | Média de `Dt. Pagamento − Dt. Vencimento` (ou `Dt. Pagamento − Data de Emissão` da fatura, se preferir DSO clássico) para faturas com `Baixado = Sim` |
| Taxa de inadimplência / atraso de recebimento | % de `FaturaReceber` com `Baixado = Não` e `Dt. Vencimento` já vencida na data de análise |
| Mix de forma de pagamento | Distribuição de `Tipo de Pagamento` (PIX vs. Boleto Bancário) sobre valor total recebido |
| Concentração de receita por cliente (Pareto) | % da receita total vinda dos top 3–5 valores de `Pagador do Frete - Nome` — relevante para risco de dependência de cliente único |
| Concentração de custo por fornecedor/transportador | % do total de `PagamentoFornecedor.Valor` (Centro de Custo = "FRETES TERCEIROS") por `Fornecedor` — identifica dependência de poucos agregados/terceiros |
| Divergência Receita Emitida vs. Faturada | `Σ CTe.Total` vs. `Σ FaturaReceber.Valor Total` — gap indica CT-e não faturado ou fatura órfã |
| Ticket médio de pagamento a terceiro por contrato | Média de `valor_total_contrato` (adiantamento + saldo) |
| Rota mais frequente / mais rentável (proxy) | Agrupar por par `Local de Coleta` → `Local de Entrega`, cruzando com receita e custo alocado onde disponível |

---

## 6. Riscos de Qualidade de Dado Observados

1. **`Centro de Custo` nulo (NaN) em despesas não-frete.** Impede diferenciar "despesa operacional genérica" de "custo direto de frete" automaticamente — hoje só a presença de `"FRETES TERCEIROS"` é confiável; tudo mais precisa de classificação manual ou de dicionário de fornecedores (ex. mapear "REDE DOM PEDRO DE POSTOS LTDA" → categoria "Combustível").
2. **`Favorecido - Nome` vazio quando o beneficiário é pessoa física** (motorista autônomo). Isso quebra tanto a identificação do fornecedor quanto qualquer heurística de match por nome na Camada 2 — sem nome, não há candidato de match algum, forçando direto para a fila manual (Camada 3).
3. **CNPJ armazenado como float / notação científica** (ex. "6.348688e+12"). Perda de precisão e de zeros à esquerda — um CNPJ brasileiro tem 14 dígitos fixos; se a exportação converteu para número, o valor original pode estar irrecuperável sem re-exportar como texto. Isso é risco direto para: (a) deduplicar remetente/destinatário/fornecedor por CNPJ; (b) cruzar `Remetente - CNPJ`/`Destinatário - CNPJ` do CT-e com `Favorecido - CNPJ` de Contas Pagar como heurística adicional de match. **Ação recomendada:** re-exportar as 3 planilhas formatando colunas de CNPJ/CPF como texto antes de qualquer carga no modelo de dados.
4. **Observação como texto livre, não campo estruturado.** Toda a ponte de reconciliação (Camadas 1 e 2) depende de regex sobre um campo digitado manualmente — sujeito a erro de digitação, abreviação inconsistente ("Cta." vs "Contrato"), e ausência total em alguns registros. Não há garantia de cobertura 100%; o desenho já assume isso (daí a Camada 3).
5. **Duas séries numéricas desconexas (CT-e vs. Contrato de Transporte).** Confirmado nos dados de exemplo (contratos 68/69 vs. CT-e's 24/382/384/385/386) — não há relação aritmética ou de intervalo aparente entre as séries, então nenhuma heurística baseada em proximidade numérica é viável; só nome/data/valor.
6. **Ausência de campo de data em `Contas Pagar.xlsx`** (não foi citada nenhuma coluna de data nessa planilha, diferente de CT-e e Contas Receber). Isso enfraquece a Camada 2 (heurística por janela de data), pois não há certeza de que exista uma data de pagamento/lançamento utilizável — **PREMISSA A VALIDAR**: confirmar com a planilha real se existe coluna de data em Contas Pagar não mencionada no escopo desta tarefa.
7. **Fatura sem número de identificação explícito.** As colunas listadas para Contas Receber não incluem um "Número da Fatura" — apenas Cliente + Observação + valores. Se não existir, cada fatura precisa de uma chave substituta (surrogate), o que é aceitável, mas dificulta rastreabilidade externa (ex. conferência com o cliente).
8b. **Nome de cliente inconsistente entre lançamentos — RESOLVIDO.** Confirmado no lote de 18
relatórios reais (maio/junho/julho): "MINERVA S.A." e "MINERVA S A" apareciam como duas linhas
separadas no ranking de rentabilidade por cliente, distorcendo Pareto e concentração de receita.
Implementado em `app/services/client_identity.py`: normalização **determinística** (maiúsculas,
sem acento/pontuação, colapso de espaço, equivalência só de sufixo societário padrão — S/A,
S.A., S A → SA; LTDA./LTDA → LTDA) — deliberadamente **sem fuzzy-match por distância de string**,
porque isso mesclaria erroneamente empresas diferentes com nome parecido. Caso real nos mesmos
dados que prova o risco: "CHINT ELETRIC CO. LTD" (matriz na China) e "CHINT ELETRICOS AMERICA DO
SUL LTDA" (subsidiária brasileira) são pagadores de frete distintos e continuam separados após a
normalização. Validado contra os 30 nomes distintos reais do trimestre: só o par MINERVA
mesclou; nenhum outro par foi indevidamente unificado. O nome de exibição escolhido por grupo é
o mais frequente nos lançamentos (empate: mais longo; novo empate: ordem alfabética — regra
determinística, testada em `tests/unit/test_client_identity.py`).

8c. **"JC COIMBRA II DISTRIBUI��O SA" — nome de cliente com caractere corrompido na origem.**
Confirmado lendo o `.xlsx` real (`Ct-e filial maio.xlsx`) diretamente com pandas: a corrupção já
está no arquivo de origem, não é um bug de import/encoding deste projeto. Provável perda de
"ÇÃ" em "DISTRIBUIÇÃO" na exportação do sistema de origem da TRIXLOG. Não corrigido
automaticamente (violaria a regra de nunca inventar dado — mesmo um "conserto" de acentuação
óbvio é uma inferência, não um fato lido). Fica registrado para correção manual num cadastro de
clientes canônico futuro, ou reporte à TRIXLOG do problema na exportação de origem.

9. **`Pedágio` pode ou não estar incluso em `Total`/`Subtotal`** — a relação aritmética entre `Valor do Frete + Valor do Frete Peso + Pedágio = Subtotal = Total` não foi confirmada nos dados citados. Antes de montar a DRE por viagem (seção 3.1), validar essa fórmula com uma amostra de linhas reais para não contar Pedágio em duplicidade ou subtraí-lo quando já é repasse líquido.

10. **Custo direto por veículo de frota própria não tem chave nos relatórios atuais — RESOLVIDO
como gap explícito, não como estimativa.** Auditoria pedida pela Tatiana (2026-08-15): a
TRIXLOG opera 5 veículos próprios confirmados nos CT-e's reais (placas TBI2D64, TBI2D63,
RTO6I76, RTO6I77, RME4C95 — `CTe.proprietario_veiculo_nome` em {"TRIXLOG TRANSPORTES LTDA",
"AP TUPY TRES CORACOES LTDA" — a segunda confirmada pela Tatiana como a própria TRIXLOG, não
um agregado}). A receita por placa é real e confiável porque o CT-e carrega a placa. O custo
direto (combustível R$ 382.389,70 e manutenção R$ 36.741,93 no trimestre, categorias reais em
`PagamentoFornecedor.centro_custo`) **não tem nenhuma referência de placa** — só posto/oficina
+ valor + data. Pedágio pago pela frota nas estradas (custo, distinto do `CTe.pedagio` que é
cobrado do cliente e é receita repassada) **não existe em nenhum lançamento** dos 3 relatórios
recebidos até agora. Ver `app/services/fleet_analytics.py` — nunca ratear esses custos
agregados por veículo sem uma chave real; a tela "Frota própria" mostra "não determinável"
explicitamente em vez de estimar. **Dado pendente para fechar esta análise**: um relatório com
placa por lançamento (cartão-combustível, telemetria/rastreador, ou controle de manutenção por
veículo, e um relatório de pedágio pago pela frota).

10a. **Carta Frete — RESOLVE custo direto de frete terceiro/agregado, NÃO resolve frota própria
— achado real, não confundir os dois.** A Tatiana enviou "Carta Frete" (6 arquivos reais,
mai/jun/jul, matriz+filial, 100 linhas úteis) — documento real de acerto com motorista/
transportador terceiro (CIOT). Tem `CTRC` que é o mesmo número de `CTe.cte_numero` — join
determinístico, não heurístico, validado batendo o Valor Total exato em casos reais (CTRC 4 →
CT-e 4 = R$ 6.044,00 idêntico; CTRC 321 matriz → CT-e 321 matriz = R$ 4.200,00 idêntico). Virou
a **Camada 0** do Cost Allocation Engine (`app/services/cost_allocation/camada0_carta_frete.py`)
— roda antes da Camada 2, é mais confiável, nunca é reprocessada por ela. Custo direto = `Frete
do Motorista + Pedágio (Despesa)`. **Confirmado real: zero interseção entre as placas da Carta
Frete e as 5 placas de frota própria** — é estritamente frete terceiro/agregado, então isto
**não fecha** o gap do item 10 acima (frota própria continua "não determinável"). Nunca usa o
campo `Lucro` da planilha como margem — a plataforma recalcula com a fórmula própria
(`rentabilidade_engine.py`), que pode diferir da fórmula do sistema de origem.

**CTRC multi-valor (achado real, não hipotético):** uma carta-frete pode cobrir várias viagens
numa linha só — `CTRC="371,374,376,377,380"` (carta 69/matriz) e uma linha com 13 números (carta
77/matriz). Regra de rateio (mesma do PRP original da Tatiana, seção 16): `participação_cte =
receita_cte / receita_total_dos_ctes_da_carta`; `custo_cte = custo_carta × participação_cte`.
Marcado `metodo_vinculo="carta_frete_rateado"` com confiança 0,8 (vs. 1,0 do link 1:1 direto) —
a UI precisa deixar visualmente claro que é uma alocação gerencial, não um valor direto do
documento. **Ambiguidade real também encontrada e tratada**: CT-e 309/filial aparece no CTRC de
duas cartas-frete diferentes (105 e 111) no mesmo arquivo — erro/duplicidade na origem. Nenhuma
das duas linka automaticamente; cai para conciliação manual, igual a qualquer ambiguidade da
Camada 2 (nunca escolher arbitrariamente entre candidatos).
