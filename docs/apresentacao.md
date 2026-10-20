---
marp: true
paginate: true
title: Pontua+ · Pontos no Pix
---

# Pontua+ · Pontos no Pix
### O que aconteceu, o que é verdade e o que fazer

Dados de 01/10/2025 a 30/09/2026 · extração 01/10/2026
Todos os números saem de `python -m pipeline.eda` e são cobertos por testes

---

## 1. O Pix somou volume, não roubou volume

- Lançado em 27/05/2026, taxa de **R$ 0,019 por ponto** em 100% das transações
- Pontos resgatados/mês: **~19–22 M → ~30–33 M** (fev–mai vs jun–set)
- Aéreas e varejo **estáveis em valor absoluto**; o Pix é volume incremental
- 2.140 usuários usaram Pix; **56% nunca tinham resgatado** antes
- Cancelamento + inválido no Pix: 13,0% vs 6,9% nas demais modalidades

---

## 2. Metas: aéreas ok, varejo abaixo desde junho

| | fev–abr/26 | jun–set/26 |
|---|---|---|
| Aéreas (meta ≥ 50%) | 79–81% | **56–59%** ✓ |
| Varejo (meta ≥ 20%) | 19–21% | **12–13%** ✗ |
| Pix | — | 28–30% |

- Varejo já estava no limite antes do Pix (abr = 19,3%)
- Cai porque o Pix entra no **denominador**. Sem ele: aéreas 81–83%, varejo 17–19% (ainda abaixo de 20%)
- **A confirmar:** o contrato inclui o Pix no denominador? Transferências contam como varejo?

---

## 3. Saúde financeira: o Pix é o ponto mais caro

| Modalidade | R$ por ponto (líquido de copagamento) |
|---|---|
| **Pix** | **0,0190** |
| Aéreas | 0,0150 |
| Varejo produtos | 0,0139 |
| Transferência parceiros | 0,0125 |

- O case diz que aéreas já custam mais que o banco paga por ponto → o Pix custa ainda mais
- Passivo em aberto: **377,7 M pontos**
- **Falta:** quanto o banco paga por ponto

---

## 4. Afirmação do CRM: "a comunicação explica o sucesso do Pix"

**Não se sustenta.**

| Grupo | Adoção do Pix |
|---|---|
| Não recebeu o e-mail | 18,0% |
| Recebeu, não abriu | 18,3% |
| Recebeu e abriu | 17,8% |

- A campanha começou em 28/05 13:00, **um dia depois** do lançamento
- 489 usuários usaram Pix sem nunca receber a campanha
- Ressalva: o CRM não tem grupo de controle; é evidência observacional (grupos comparáveis: 32% de resgatadores prévios em todos)

---

## 5. Afirmação do operador: "o Pix sai a ~R$ 0,016 por ponto"

**Falsa: erro de cálculo no relatório.**

- Taxa real: R$ 0,019 em todos os 3.292 itens Pix
- O relatório divide **R$ dos Pix aprovados** por **pontos de todos os status**, inclusive cancelados e inválidos, que não pagaram nada
- Jun/26: 10.709.419 pontos reportados = soma de todos os status; aprovados = 9.215.135
- O relatório também muda de critério em junho nos percentuais de categoria

---

## 6. Afirmação do diretor: "breakage em 40%"

**Não reproduzível e ainda não mensurável.**

- Nenhum ponto do programa novo expirou: o primeiro vence em **25/09/2027**
- Só existem expirações de saldo migrado: expirado/migrado = **19,8%**
- Expirado/resgatado em fev–mai = 37,1%, provável origem do "40%", mas essa razão não é breakage
- Inconsistência: saldo migrado tem validade até 31/03/2028, mas expira desde jan/26, inclusive em 1.805 contas sem crédito de migração

---

## 7. Cuidados com os dados

- `orders.user_id` vem vazio → usuário vem de `carts`
- "Cashback" mistura Pix com **compra de pontos** (não é resgate)
- "Varejo" inclui transferências para parceiros
- Lote atípico em **12/01/2026**: 1.520 resgates de aéreas em 24 h (76 M pontos) → janeiro mostra aéreas em 97%
- Ledger e pedidos **conciliam ao ponto**: 323.423.650 pontos resgatados

---

## 8. Recomendação

1. **Recalibrar o Pix**: taxa ≤ R$ 0,015 ou teto mensal por cliente → hoje é o ponto mais caro (0,019)
2. **Manter o Pix** como ativação → 56% dos usuários do Pix eram inativos
3. **Plano de varejo** com parceiros próprios → varejo em 12–13%, meta de 20%
4. **Corrigir o relatório do operador** → R$ 0,016 é artefato de cálculo
5. **Grupo de controle** nas próximas campanhas → hoje não dá para medir efeito
6. **Redefinir breakage** → 40% não se reproduz; só mensurável a partir de set/2027
7. **Auditar 12/01/2026**

**Falta saber:** preço por ponto pago pelo banco · definição contratual das metas · fórmula do breakage
