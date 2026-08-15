# Caso de referência — viagem sem alocação de custo confirmada

> Números abaixo são fictícios (estrutura real, valores inventados para teste), servem para
> testar o comportamento dos agentes sobre o problema central do projeto: rentabilidade sem
> chave de alocação de custo confiável.

## Situação
CT-e nº 412, série 1, emitido em 2026-07-15, pagador do frete "AGROVALE INDÚSTRIA LTDA",
rota Varginha/MG → Uberlândia/MG, Total R$ 7.200,00 (frete + pedágio).

Em Contas a Pagar, no mesmo período, há 6 lançamentos de "FRETES TERCEIROS" referenciando
"Contrato de Transporte número 91", "92", "94", "95", "97" e "99" — nenhuma Observação menciona
o CT-e 412 nem o Conhecimento 000412.

## Pergunta de decisão
Qual é a margem real desta viagem, e o que fazer quando a chave de alocação não fecha
automaticamente?

## O que a Camada 1 (regex) encontra
Nenhum contrato referencia "Conhecimento 000412" ou "CT-e 412" no texto de Observação — falha de
cobertura da Camada 1 para este caso específico.

## O que a Camada 2 (heurística) encontra
Dois contratos (94 e 97) foram pagos a fornecedores cujo nome aparece também como
"Proprietário do Veículo" em CT-e's da mesma semana na mesma região (Sul de Minas), dentro de
uma janela de ±3 dias da data de emissão do CT-e 412 — **dois candidatos, não um só**. A regra
de negócio (`docs/COST_ALLOCATION.md` Camada 2) exige match único; com dois candidatos, o caso
cai automaticamente para a Camada 3.

## Diagnóstico esperado
- FATO: CT-e 412 gerou receita de R$ 7.200,00 para o cliente AGROVALE INDÚSTRIA LTDA.
- FATO: nenhum custo de frete terceiro foi vinculado automaticamente a esta viagem com confiança alta.
- CÁLCULO: margem bruta desta viagem = **"não determinável — custo não alocado"**, nunca R$ 7.200,00
  apresentado como lucro nem custo médio da rota aplicado silenciosamente como se fosse fato.
- O sistema **não pode** ratear um custo médio histórico da rota e apresentar isso como a margem real
  — isso violaria a regra central do projeto (nunca inventar dado apresentado como fato).

## O que NÃO fazer
- Não atribuir automaticamente o contrato 94 ou 97 sem decisão humana, mesmo que um "pareça mais
  provável" — a regra de ambiguidade (2+ candidatos) exige conciliação manual.
- Não descartar a viagem da análise de rentabilidade — ela deve aparecer na Reconciliation Queue,
  não desaparecer silenciosamente.
- Não tratar isso como "erro do sistema da empresa" — é uma lacuna estrutural conhecida e
  esperada (ver `docs/COST_ALLOCATION.md`), com fluxo de correção definido.

## Saída esperada da torre de controle
1. CT-e 412 aparece na Reconciliation Queue com os 2 candidatos sugeridos (contratos 94 e 97),
   ordenados por proximidade de data/nome.
2. Um operador humano confirma um dos dois (ou busca outro, ou marca "sem custo de terceiro
   identificável").
3. A decisão manual fica registrada com `metodo_vinculo=manual`, `confianca_vinculo=1.0`, e os
   atributos que levaram à escolha — isso alimenta a calibração futura da Camada 2.
4. Só depois desta decisão a viagem entra no cálculo de rentabilidade por cliente da AGROVALE
   INDÚSTRIA LTDA.

## Critério de encerramento
- Viagem vinculada (manual ou automaticamente com confiança alta) ou explicitamente marcada
  "sem custo de terceiro identificável" (ex.: veículo próprio);
- decisão registrada com dono e timestamp;
- rentabilidade da AGROVALE recalculada incluindo esta viagem.
