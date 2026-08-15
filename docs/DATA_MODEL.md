# Modelo de dados — fonte de verdade: relatórios reais da TRIXLOG

Este documento não é hipotético. As entidades `CTe`, `FaturaReceber` e `PagamentoFornecedor`
vêm campo a campo dos 3 relatórios reais em `examples/` (`cte_real.xlsx`, `contas_receber_real.xlsx`,
`contas_pagar_real.xlsx`). `ContratoTransporte` e `Viagem` são inferidas — não existem como
planilha própria hoje. Ver `docs/COST_ALLOCATION.md` para a lógica completa de alocação.

## CTe (receita — fonte: CT-e.xlsx, 68 linhas reais)

Unidade atômica de receita. Chave primária: `(cte_numero, cte_serie)`.

- `cte_tipo` (CT-e | 67) · `cte_numero` · `cte_serie` · `data_emissao`
- `local_coleta` · `local_entrega` · `cfop`
- `pagador_frete_nome` — **define "cliente" para rentabilidade**, não necessariamente igual a remetente/destinatário
- `remetente_nome/endereco/cidade/cnpj` · `destinatario_nome/endereco/cidade/cnpj`
- `proprietario_veiculo_nome` · `veiculo_placa` · `motorista_nome`
- `valor_frete` · `valor_frete_peso` · `pedagio` · `subtotal` · `total`
- `modal` (observado sempre "Rodoviário") · `data_entrega` · `ultima_ocorrencia`

**Risco de dado real:** CNPJ pode chegar como float/notação científica (`6.348688e+12`) — reexportar
como texto antes de carregar, senão perde dígito e quebra qualquer match por CNPJ.

## FaturaReceber (fonte: Contas Receber.xlsx, 46 linhas reais)

- `cliente_nome` · `centro_receita` (visto: "FRETE - CTE") · `valor_total`
- `dt_vencimento` · `baixado` (Sim/Não) · `dt_pagamento` · `valor_pago` · `tipo_pagamento` (PIX, Boleto)
- `observacao_raw` — contém "Fatura ref. ao(s) Conhecimento(s) NNNNNN" (pode referenciar vários CT-e's numa fatura só)
- `ctes_referenciados[]` — **derivado**, parse de `observacao_raw`

Não há coluna de número de fatura explícita nos campos vistos — **PREMISSA A VALIDAR**.

## PagamentoFornecedor (fonte: Contas Pagar.xlsx, 79 linhas reais)

- `fornecedor_nome` · `centro_custo` (visto: "FRETES TERCEIROS"; NaN para outras despesas)
- `valor` · `favorecido_nome/cnpj/banco/agencia/conta/pix`
- `observacao_raw` — contém "Contrato de Transporte número NN" quando é frete terceirizado
- `contrato_transporte_numero` — **derivado**
- `tipo_parcela` (Adiantamento | Saldo) — **derivado**, cada contrato gera exatamente 2 pagamentos

Só é custo de frete direto quando `centro_custo = "FRETES TERCEIROS"` **e** a observação referencia
um contrato. Combustível/insumo (`centro_custo = NaN`) não tem vínculo a CT-e nestes exports.

## ContratoTransporte (inferida — não existe como planilha própria)

Reconstruída agrupando `PagamentoFornecedor` por `contrato_transporte_numero`:
`valor_adiantamento` + `valor_saldo` = `valor_total_contrato`. **Numeração independente da
numeração de CT-e** (contratos vistos: 68, 69; CT-e's vistos: 24, 382, 384, 385, 386 — sem
relação aritmética). Esta é a raiz do problema: nenhuma FK direta liga `ContratoTransporte` a `CTe`.

## Viagem (entidade central a construir — não existe fonte primária)

Resultado do processo de conciliação, não um import direto:

| Campo | Origem |
|---|---|
| `viagem_id` | surrogate key |
| `cte_numero` (1..N) | CTe |
| `contrato_transporte_numero` (0..N) | ContratoTransporte |
| `metodo_vinculo` | `regex_observacao` \| `heuristica_placa_data` \| `manual` \| `nao_vinculado` |
| `confianca_vinculo` | 0.0–1.0 |
| `receita_total` | Σ CTe.total dos CT-e's vinculados |
| `custo_frete_terceiro` | ContratoTransporte.valor_total_contrato vinculado |
| `margem_contribuicao_bruta` | receita_total − custo_frete_terceiro |

## Entidades de produto (Decision Queue, mesmo contrato do SAL AI OS)

`MetricDefinition`, `Alert`, `Diagnosis`, `Hypothesis`, `Recommendation`, `Decision`,
`ActionExecution`, `OrganizationalLearning` — ver `schemas/*.json`. Mesma estrutura já validada
no SAL Intelligence OS; `diagnosis.schema.json` continua exigindo exatamente 3 recomendações
(contenção/estrutural/otimização).

## Módulo de cotação de frete

Ver `docs/QUOTING_MODULE.md` — `SolicitacaoCotacao`, `Cotacao` (venda), `CotacaoCompra` (compra a
terceiro), com máquina de estados e guardrail de margem mínima. Funcionalidade nova, sem dado
histórico — desenhada a partir de prática de mercado, marcada como premissa a validar.
