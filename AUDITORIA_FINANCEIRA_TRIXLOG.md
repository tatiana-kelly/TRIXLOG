# Auditoria Financeira, Operacional e de Dados — TRIXLOG Torre de Controle

**Auditor:** Claude (papel de Auditor Independente, a pedido da Tatiana)
**Data:** 2026-08-16
**Escopo dos dados:** trimestre maio–julho/2026, matriz + filial, 337 CT-e's, 100 Cartas Frete, 253 Faturas a Receber, 341 Pagamentos a Fornecedor
**Fonte:** Postgres real (Supabase, projeto `nhymlpubpxbyibulezwj`), repositório `github.com/tatiana-kelly/TRIXLOG`

Princípio seguido nesta auditoria: **não fazer os números fecharem — descobrir se estão certos e provar a origem.** Nenhum valor foi ajustado só para bater. Onde a auditoria não conseguiu confirmar nem descartar algo, isso fica registrado como risco, não como fato.

---

## 1. Resumo executivo

A auditoria cobriu a DRE inteira (receita, frete terceiro, combustível, manutenção, despesas operacionais e financeiras) e investigou duas rodadas de divergências levantadas pela Tatiana. **Nenhum bug de dupla contagem foi encontrado.** A DRE reconcilia exatamente (diferença R$ 0,00 em todas as linhas, tolerância de R$ 0,05) quando recalculada por um caminho de código independente — ver seção 7.

**Um risco real e novo foi encontrado e agora está exposto, não corrigido às cegas**: R$ 8.386,85 (trimestre) / R$ 4.786,85 (julho) de vale-combustível pago a motorista terceiro (campo `Adto. Vale Abastec.` da Carta Frete) pode se sobrepor com a linha "Combustível" da DRE, que vem de uma fonte totalmente independente (Contas a Pagar). Os dois relatórios não compartilham nenhuma chave (motorista, placa, contrato) que permita confirmar ou descartar a sobreposição — por isso ela é **declarada, nunca deduzida automaticamente**.

**Divergências que a Tatiana apontou e que a auditoria não conseguiu reproduzir** (Manutenção R$ 11.950,14 vs R$ 11.180,14; Administrativas R$ 14.685,00 vs R$ 10.085,00): testadas contra três agrupamentos independentes dos dados reais, nenhum reproduz os valores apontados — os números da DRE são internamente consistentes entre si. Provavelmente estimativas aproximadas feitas à mão sobre a planilha bruta (a própria mensagem as descreve como "aproximadamente"), não erros da plataforma.

---

## 2. Divergências encontradas

| # | Divergência apontada | Resultado da investigação |
|---|---|---|
| 1 | Frete terceiro julho: Carta Frete R$ 269.300,00 vs DRE R$ 292.249,98 (dif. R$ 22.949,98) | **Explicada por completo** — os dois números medem coisas diferentes (ver seção 7). Não é erro. |
| 2 | Frete terceiro julho: Contas a Pagar (centro de custo) R$ 258.350,00 vs DRE R$ 292.249,98 | **Explicada por completo** — Contas a Pagar por essa ótica é pagamento, não custo por competência (ver seção 7). Não é erro. |
| 3 | Manutenção julho: R$ 11.950,14 apontado vs R$ 11.180,14 da DRE | **Não reproduzida.** DRE consistente com `dt_emissao` e `arquivo_origem` reais. |
| 4 | Administrativas julho: R$ 14.685,00 apontado vs R$ 10.085,00 da DRE | **Não reproduzida.** Mesmo resultado do item 3. |
| 5 | Vale-combustível de terceiro pode se sobrepor com Combustível da DRE | **Confirmada como risco real, não como erro comprovado** — quantificada e exposta (seção 8). |

---

## 3. Duplicidades encontradas

**Nenhuma duplicidade de custo foi encontrada na DRE.** Verificação estrutural: cada `ViagemLink` (a entidade que liga CT-e a custo) usa **ou** `custo_direto` (vindo de Carta Frete) **ou** `contrato_transporte_numero` (vindo de Contas a Pagar) — nunca os dois ao mesmo tempo. Isso é garantido pelo código (`app/services/custo_lookup.py`), não por convenção.

Verificação empírica adicional: dos 4 CT-e's de julho resolvidos via Contas a Pagar (Camada 2), **nenhum** tem Carta Frete correspondente (CTRC checado um a um) — não há concorrência entre as duas fontes para o mesmo CT-e.

**Duplicidade real encontrada, mas do lado do dado de origem, não do cálculo**: o CT-e 309/filial é referenciado no CTRC de duas Cartas Frete diferentes (números 105 e 111) no mesmo arquivo — erro/duplicidade no sistema de origem da TRIXLOG. A plataforma não escolhe nenhuma das duas automaticamente; o CT-e fica pendente de conciliação manual (R$ 3.700,00 de custo potencial, não contabilizado em lugar nenhum até uma decisão humana).

---

## 4. Valores incorretamente somados

Nenhum valor incorretamente somado foi encontrado na lógica atual. Especificamente verificado, a pedido: `Frete do Motorista` é usado como o **único** valor de custo por Carta Frete — os campos `Adto. Carta Frete`, `Adto. Vale Abastec.`, `Adto. Taxas`, `Saldo`/`Frete Líquido` **nunca são somados por cima** dele. Isso já era a implementação antes desta auditoria (confirmado lendo `app/services/importers/carta_frete_importer.py` e `app/services/cost_allocation/camada0_carta_frete.py`), não uma correção feita agora.

---

## 5. Regras anteriores incorretas

Nenhuma regra de cálculo precisou ser corrigida nesta rodada. A única mudança de código foi **aditiva** (capturar um campo que não era lido antes — `Adto. Vale Abastec.` — e expor um risco, não alterar nenhuma fórmula existente).

---

## 6. Regra correta proposta (confirmada, já implementada)

- **Receita** = `SUM(CTe.Total)`, sempre, sem exceção.
- **Custo de frete terceiro** = `Frete do Motorista + Pedágio (Despesa)` da Carta Frete (Camada 0, prioridade) **ou** `valor_total_contrato` reconstruído de Contas a Pagar (Camada 2, só quando não há Carta Frete) — nunca os dois juntos para o mesmo CT-e.
- **Frota própria** (5 placas: TBI2D64, TBI2D63, RTO6I76, RTO6I77, RME4C95) nunca usa Carta Frete — confirmado real, zero interseção de placa entre os dois universos.
- **Combustível/Manutenção** = soma agregada real de Contas a Pagar, sem chave de placa — não confirmado que é só das 5 placas próprias (rótulo da UI já deixa isso explícito).
- **Competência × pagamento**: a DRE usa a data de emissão do CT-e (competência econômica), nunca a data de pagamento — por isso um documento de acerto emitido em julho, mas referente a viagem de junho, corretamente não entra na DRE de julho.

---

## 7. Reconciliação de Frete Terceiro (julho/2026)

| Fonte | O que mede | Valor | Por que difere da DRE |
|---|---|---:|---|
| Carta Frete — soma bruta `Frete do Motorista`, arquivos "julho" | Todo o valor contratado nos documentos emitidos em julho, ligados ou não a um CT-e | R$ 269.300,00 | R$ 29.149,99 desse valor liquida CT-e's cuja **competência real é junho** (documento emitido depois da viagem); R$ 3.700,00 fica pendente por ambiguidade (CT-e 309/filial, 2 cartas) |
| Contas a Pagar — centro de custo `FRETE TERCEIRO`/`FRETES TERCEIROS`, por data de pagamento | Pagamentos (adiantamento+saldo) datados de julho, de contratos que podem ser de qualquer competência | R$ 258.350,00 (73 lançamentos) | É visão de **caixa**, não de competência; a DRE usa só a fatia desses contratos que resolve CT-e's sem Carta Frete (R$ 55.800,00, 4 CT-e's) |
| **DRE — custo confirmado, CT-e's com competência = julho** | O que a Torre de Controle reconhece como custo de julho | **R$ 292.249,98** | — |

Decomposição exata do R$ 292.249,98: R$ 236.449,98 (Carta Frete, CT-e's realmente de julho: 35 links diretos + 13 rateados) + R$ 55.800,00 (Contrato/Contas a Pagar, 4 CT-e's sem Carta Frete).

Detalhe registro-a-registro disponível ao vivo na plataforma: tela **Qualidade dos Dados → Custo direto — Frete terceiro → ⓘ ver origem**.

---

## 8. Reconciliação de Combustível

| Item | Valor (julho) | Valor (trimestre) |
|---|---:|---:|
| Combustível bruto — Contas a Pagar, `centro_custo=COMBUSTÍVEIS` | R$ 336.829,90 | R$ 382.389,70 |
| Vale-combustível de terceiro (Carta Frete, `Adto. Vale Abastec.`) — **risco de sobreposição, não deduzido** | R$ 4.786,85 | R$ 8.386,85 |
| Combustível econômico reconhecido na DRE (sem dedução) | R$ 336.829,90 | R$ 382.389,70 |

**Por que não foi deduzido**: `PagamentoFornecedor` (Contas a Pagar) não tem nenhum campo que referencie motorista, placa, CTRC ou contrato — não existe chave para confirmar que um lançamento específico de "COMBUSTÍVEIS" é, de fato, o pagamento do vale-abastecimento de um terceiro específico. Subtrair R$ 8.386,85 sem essa prova seria inventar um número. A plataforma expõe o risco (tela Qualidade dos Dados e alerta na DRE) e aguarda um relatório de origem que ligue os dois eventos (ex.: nota fiscal do posto referenciando o motorista/placa, ou um relatório de conciliação de vale-combustível).

Nenhum abastecimento foi automaticamente atribuído às 5 placas próprias — a plataforma nunca fez isso.

---

## 9. Reconciliação de Frota Própria

| Placa | Viagens | Receita (real, via CT-e) | Custo direto por veículo |
|---|---:|---:|---|
| RTO6I76 | 41 | R$ 231.145,26 | não determinável |
| TBI2D63 | 36 | R$ 209.263,52 | não determinável |
| RTO6I77 | 29 | R$ 171.983,60 | não determinável |
| TBI2D64 | 28 | R$ 158.878,17 | não determinável |
| RME4C95 | 13 | R$ 92.653,59 | não determinável |

A receita por placa é 100% real e confiável (o CT-e carrega a placa). O custo direto por veículo continua **não determinável** — nem Combustível nem Manutenção de Contas a Pagar têm chave de placa. Isso não é uma lacuna desta auditoria; já estava documentado (`docs/COST_ALLOCATION.md#10`) antes desta rodada e segue sem solução até chegar um relatório com placa por lançamento (cartão-combustível, telemetria, ou controle de manutenção por veículo).

---

## 10. Reconciliação de Contas a Pagar

341 lançamentos reais, classificados por `centro_custo`: Frete Terceiro (184 linhas, alimenta Camada 2), Manutenção de Frota (47), Combustíveis (20), Licença de Software (20), Administrativas — Mão de Obra (19) e Geral (12), Medicina do Trabalho (4), Despesas Financeiras (2), Seguros (1), Cofins (1), 31 sem centro de custo classificado. Todas as categorias que alimentam a DRE foram reconciliadas nesta auditoria (seções 7 e 8, mais Administrativas/Software/Medicina/Seguros/Financeiras verificadas linha a linha na tela Qualidade dos Dados). Não foi construído ainda um módulo de aging/vencimento para Contas a Pagar em si (fora do escopo desta auditoria financeira, é um módulo de UI pendente).

---

## 11. Reconciliação de Contas a Receber

253 faturas reais importadas. Contas a Receber **não é somado como receita adicional** — a receita da DRE vem exclusivamente do CT-e (`SUM(CTe.Total)`), nunca de Contas a Receber, exatamente como pedido. Contas a Receber hoje só é usado para contagem/status na tela "Visão geral" — ainda não existe um módulo dedicado de aging/inadimplência (é trabalho pendente, não um achado de erro).

---

## 12. DRE antes × DRE auditada

| Indicador | Antes desta auditoria | Depois da auditoria | Diferença | Motivo |
|---|---:|---:|---:|---|
| Receita Operacional (julho) | R$ 768.630,54 | R$ 768.630,54 | R$ 0,00 | Confirmado correto, sem alteração |
| Custo direto — Frete terceiro (julho) | R$ 292.249,98 | R$ 292.249,98 | R$ 0,00 | Confirmado correto, sem alteração |
| Combustível (julho) | R$ 336.829,90 | R$ 336.829,90 | R$ 0,00 | Confirmado correto — **nota de risco adicionada**, valor não alterado |
| Manutenção (julho) | R$ 11.180,14 | R$ 11.180,14 | R$ 0,00 | Confirmado correto, sem alteração |
| Resultado Gerencial (julho) | R$ 109.322,90 | R$ 109.322,90 | R$ 0,00 | Sem alteração |
| *(novo)* Risco de sobreposição — vale-combustível terceiro | não existia | R$ 4.786,85 (julho) / R$ 8.386,85 (trimestre) | — | Campo novo, capturado e exposto pela primeira vez nesta auditoria |

**Nenhum número da DRE mudou de valor nesta auditoria** — a auditoria confirmou que os números já estavam certos, e adicionou uma disclosure nova (o risco do vale-combustível) que antes nem era capturada.

---

## 13. Itens ainda não conciliados

1. **CT-e 309/filial** — R$ 3.700,00, reivindicado por duas Cartas Frete (105 e 111). Pendente de decisão humana.
2. **R$ 8.386,85 de vale-combustível de terceiro** — risco de sobreposição com Combustível, sem chave para confirmar ou descartar.
3. **215 CT-e's (R$ 1.180.213,56 em receita, todo o período)** sem nenhuma fonte de custo de frete terceiro — não são custo zero, ficam de fora do cálculo de margem.
4. **Custo direto por veículo de frota própria** — segue não determinável (combustível/manutenção sem chave de placa).
5. **31 lançamentos de Contas a Pagar sem `centro_custo` classificado** — não entram em nenhuma categoria da DRE hoje.

---

## 14. Riscos de dados

- Vale-combustível de terceiro (seção 8) — o maior risco financeiro quantificado desta auditoria.
- Ambiguidade de CTRC entre cartas-frete diferentes (item 13.1) — sinal de erro de digitação recorrente possível na origem.
- Categorias de Contas a Pagar sem chave de placa/motorista/CT-e (Combustível, Manutenção) — impede qualquer análise abaixo do nível "empresa/unidade" até chegar um relatório com essa chave.
- "JC COIMBRA II DISTRIBUIÇÃO SA" com caractere corrompido na origem (achado anterior, documentado em `docs/COST_ALLOCATION.md#8c`) — não é um problema desta auditoria financeira, mas seguem no mesmo lote de riscos de qualidade de dado da origem.

---

## 15. Alterações realizadas no código

- `app/models/carta_frete.py` — novo campo `adto_vale_abastecimento`.
- `app/services/importers/carta_frete_importer.py` — captura o campo `Adto. Vale Abastec.` da planilha (não lido antes).
- `app/services/dre_engine.py` — novo campo `combustivel_risco_sobreposicao_terceiro`, calculado e exposto, **nunca subtraído** do valor de Combustível.
- `app/services/audit_engine.py` — nota de risco anexada à linha "Combustível" na reconciliação, quando aplicável.
- `app/api/analytics.py` — campo novo exposto em `GET /analytics/dre`.
- `app/static/app.js` / `styles.css` — alerta visual na tela DRE quando o risco é maior que zero.
- `app/db/session.py` — migração da coluna nova no Postgres real (Supabase), com backfill dos 100 registros de Carta Frete já importados.
- `docs/COST_ALLOCATION.md` — achados desta auditoria documentados na íntegra (seção 10b).
- Testes novos: `test_dre_engine.py::test_expoe_risco_de_sobreposicao_combustivel_vs_vale_terceiro_sem_deduzir`.

**Nenhuma fórmula de cálculo existente foi alterada.** Todas as mudanças são aditivas (captura de dado novo + exposição de risco).
