# EDA · Pontua+

Análise exploratória dos 9 CSVs (versão v1). Todos os números deste documento são reproduzidos por `python -m pipeline.eda` (consultas sobre a camada silver/gold do SQLite). Legenda: **[C]** confirmado nos dados · **[H]** hipótese · **[?]** depende do negócio/dono do sistema.

## 1. Integridade da entrega

- [C] Contagem de linhas e SHA-256 dos 9 arquivos batem com `MANIFESTO_v1.csv`.
- [C] Nenhuma linha duplicada em nenhum arquivo. Todas as chaves `*_id` têm 12 dígitos (exceto `device_id` e `campaign_id` no CRM).
- [C] Datas dos sistemas transacionais (`orders`, `order_items`, `points_ledger`, `cards`) vêm todas com offset `-03:00`. O CRM (`event_ts`) vem **sem fuso**. [H] tratado como horário local; não foi possível confirmar com o alinhamento `Order Approved` × `orders` (diferenças dispersas, sem um deslocamento fixo).
- [C] Período: pedidos de 01/10/2025 a 30/09/2026; ledger desde 25/09/2025; extração em 01/10/2026.

## 2. Grão, chaves e relacionamentos

| Tabela | Grão | Chave | Observações |
|---|---|---|---|
| orders | 1 pedido | order_id | `user_id` **100% vazio** → usuário vem de `carts` via `cart_id` (1:1, 100% de match) |
| order_items | 1 item de pedido | order_item_id | 18 pedidos têm 2 itens; `quantity` sempre 1; 4 itens com status diferente do pedido |
| carts | 1 carrinho | cart_id | canal APP/WEB |
| points_ledger | 1 movimento de pontos | movement_id | sinal já embutido em `points`; `valid_until` só em créditos |
| dim_operation | 1 tipo de operação | operation_code | 7 códigos; **3 (EXPIRACAO) e 13 (ESTORNO_CREDITO) nunca aparecem** |
| cards | 1 conta/cartão | account_id | 12.000 usuários, 16.168 contas; exatamente 1 `is_most_recent=True` por usuário |
| redeemed_points | 1 movimento de pontos de 1 item (por conta) | (order_item_id, account_id, movement_type, seq) | ver §4 |
| crm_events | 1 evento | sem chave natural | 20.252 eventos sem `user_id`, todos recuperáveis por `device_id` (device→user é 1:1) |
| relatorio_mensal_cliente | 1 mês | mes | relatório do operador, não é fonte primária |

Relacionamentos validados: `order_items → orders` 100%; `orders → carts` 100%; `points_ledger.account_id → cards` 100% (e o `user_id` bate); `redeemed_points.order_item_id → order_items` 100%; usuários do CRM ⊂ `cards`.

## 3. Pegadinhas encontradas

1. **`orders.user_id` vazio.** O usuário só existe em `carts`.
2. **`category_macro = 'Cashback'` mistura duas coisas:** Pix (`TRANSFERENCIA`/`Pix Pontua+`, 3.292 itens) e **compra de pontos** (`COMPRA_PONTOS`, 520 itens, `paid_points` vazio, pago em R$). Compra de pontos **não é resgate** e foi excluída das métricas de resgate.
3. **`category_macro = 'Varejo'` inclui transferências para programas parceiros** (Nuvem Recompensas, Pontos Max) e uma agência de viagens (Decola Viagens). O README do case trata "transferências para parceiros" como modalidade separada de varejo. [?] Qual é a definição contratual de varejo?
4. **Marketplace:** `supplier_name = 'Casa&Cia (via MegaMagazine)'` tem `supplier_responsible = 'MegaMagazine'`. Usamos `supplier_name` como fornecedor e `supplier_responsible` como quem responde pelo pedido.
5. **Status.** Só `APROVADO` e `ESTORNADO` geram débito no ledger (`RESGATE`); `CANCELADO`, `INVALIDO` e `AGUARDANDO_CONFIRMACAO` não debitam pontos. `FINALIZADO_COM_SUCESSO` só existe em compra de pontos. Métricas de resgate usam **APROVADO** (resgate efetivado); estornos aparecem à parte.
6. **Conciliação ledger × pedidos fecha:** soma de `RESGATE` no ledger = soma de `paid_points` de itens APROVADO+ESTORNADO (323.423.650). Soma de `ESTORNO_PEDIDO` (3.396.211) = pontos dos itens ESTORNADO (3.141.827) + `refunded_points` parciais em itens APROVADO (254.384).
7. **`redeemed_points` não é 1 linha por item:** 1.471 itens têm **2 linhas `RESGATE`** (pagamento dividido entre 2 contas do mesmo usuário; a soma bate com `paid_points`); 5.272 itens têm o par `RESERVA`/`CANCELADO_RESERVA` (reserva liberada, efeito líquido zero). Somar `points` sem filtrar `movement_type` duplica o resgate.
8. **Pico de 12/01/2026:** 1.520 resgates de aéreas em um único dia (76,0 M pontos; o mês inteiro teve 85,6 M), distribuídos uniformemente nas 24 h, por 1.517 usuários distintos, dos quais 1.512 têm crédito de migração. A mediana do ticket dobra (45,5 mil vs 19,6 mil pontos). [H] carga em lote de reservas do programa antigo ou ação com a base migrada, não comportamento orgânico. Faz o relatório de jan mostrar aéreas 97% / varejo 3%. Sem os itens desse lote, aéreas em jan = 77,1%.
9. **Expiração inconsistente:** só existe `EXPIRACAO_MIGRACAO` (103), ~7 M pontos/mês desde 01/01/2026, mas o `valid_until` de todos os créditos de migração é **31/03/2028**. Além disso, 1.805 contas têm expiração de migração **sem nenhum crédito de migração**. Créditos normais (código 1) têm validade de 2 anos e o primeiro vence em **25/09/2027** → nenhum ponto do programa novo expirou ainda.
10. **Saldo negativo:** 1.197 contas terminam com saldo negativo no ledger e 8.708 movimentos são anteriores à criação do cartão → ledger provavelmente não contém o saldo de abertura completo ou o cadastro de cartões é sobrescrito (reemissão).
11. **CRM sem grupo de controle:** `control_group` 100% vazio. Não há como medir efeito causal de campanha com desenho experimental.
12. **Relatório do operador mistura critérios:** `pix_pontos` e `pix_transacoes` contam **todos os status** (incluindo cancelados e inválidos), mas `pix_reais` fica próximo do valor só dos aprovados. Os percentuais por categoria batem com "só aprovados" em todos os meses **exceto junho**, que bate com "todos os status".
13. **Push em agosto:** queda de ~75% nos envios de push (2.730 vs ~10–13 mil nos outros meses), confirmada no CRM e no relatório. [?] Incidente na ferramenta ou decisão de negócio?

## 4. Perguntas do case

### 4.1 O que aconteceu com os resgates depois do Pix

- [C] Pix lançado em 27/05/2026 (primeiro item às 09:15). Taxa **exatamente R$ 0,019/ponto** em 100% dos 3.292 itens.
- [C] Pontos resgatados (aprovados) por mês saem de ~19–22 M (fev–mai) para ~30–33 M (jun–set). **Aéreas e varejo em valor absoluto ficam estáveis**; o Pix é volume **incremental**, não canibalização direta.
- [C] 2.140 usuários usaram Pix; **1.195 (56%) nunca tinham resgatado nada antes** → o Pix ativa base parada.
- [C] Cancelamento + inválido no Pix: 13,0% vs 6,9% nas demais modalidades no mesmo período.

### 4.2 Metas (aéreas ≥ 50%, varejo ≥ 20% dos pontos resgatados)

| Mês | Aéreas | Varejo (categoria) | Varejo só produtos | Pix |
|---|---|---|---|---|
| fev–abr/26 | 79–81% | 19–21% | 15–16% | — |
| jun–set/26 | 56–59% | 12–13% | 11–12% | 28–30% |

- [C] Aéreas segue acima de 50%. Varejo **já ficava no limite antes do Pix** (abr = 19,3%) e cai para ~12–13% depois, porque o Pix entra no denominador.
- [?] O Pix entra no denominador da meta? Se não entrar, aéreas fica em 81–83% e varejo em 17–19% (ainda abaixo da meta).
- [?] Transferências para parceiros e agência de viagens contam como varejo?

### 4.3 Afirmação do CRM: "a comunicação de lançamento explica o sucesso do Pix"

- [C] A campanha `CMP_LANCAMENTO_PIX` (e-mail) começa em **28/05 13:00**, um dia depois do lançamento; 20 resgates Pix acontecem antes do primeiro envio.
- [C] Adoção do Pix por grupo: não recebeu = **18,0%**; recebeu e não abriu = **18,3%**; recebeu e abriu/clicou = **17,8%**. Não há diferença.
- [C] 489 usuários usaram Pix sem nunca receber a comunicação.
- [H] Conclusão: os dados **não sustentam** a afirmação. Ressalva: sem grupo de controle formal, é evidência observacional; a seleção da audiência parece aleatória (mesma proporção de resgatadores prévios nos dois grupos: 32% × 32%).

### 4.4 Afirmação do operador: "o Pix sai a cerca de R$ 0,016 por ponto"

- [C] Falsa. Em todos os itens a taxa é R$ 0,019. O relatório divide `pix_reais` (aprovados) por `pix_pontos` (todos os status, inclusive cancelados e inválidos que não pagaram nada), o que dá ~0,0163.

### 4.5 Afirmação do diretor: "breakage está em 40%"

- [C] Nenhuma definição padrão reproduz 40%. Candidatos: expirado / migrado = **19,8%**; expirado / (expirado + resgatado) = 16,5%; expirado / resgatado = 19,8% no período e **37,1% em fev–mai** (provável origem do número, mas essa razão não é breakage).
- [C] Breakage do programa novo **ainda não é mensurável**: nenhum crédito venceu (primeiro vencimento em 25/09/2027).
- [?] As expirações de migração são confiáveis, dado o conflito com `valid_until` (§3.9)?

### 4.6 Saúde financeira (custo por ponto, líquido do copagamento em R$)

| Modalidade | R$/ponto |
|---|---|
| Pix | 0,0190 |
| Aéreas | 0,0150 |
| Varejo (produtos) | 0,0139 |
| Transferência parceiros | 0,0125 |

- [C] O Pix é a modalidade **mais cara por ponto** para o programa.
- [H] `product_value` é o custo para o programa (pode ser preço de venda).
- [?] Quanto o banco paga por ponto? O README diz que aéreas custam mais do que o banco paga; se for menos que R$ 0,015, cada ponto via Pix dá ainda mais prejuízo que aéreas.
- [C] Passivo de pontos (saldo do ledger) em 30/09/2026: 377,7 M pontos.

## 5. Perguntas técnicas (para donos dos sistemas)

1. Por que `orders.user_id` vem vazio? `carts.user_id` é a fonte oficial do usuário?
2. Em que fuso está o `event_ts` do CRM?
3. O que foi o lote de 12/01/2026? É reserva migrada do programa antigo?
4. Por que `EXPIRACAO_MIGRACAO` ocorre com `valid_until` em 2028 e em contas sem crédito de migração? Os códigos 3 e 13 estão desativados?
5. O ledger tem saldo de abertura? Por que 1.197 contas ficam negativas?
6. `cards.created_at` é a data de emissão original ou da última reemissão?
7. Qual a regra do pagamento dividido entre contas (2 linhas `RESGATE`)?
8. Como o operador calcula cada coluna do relatório mensal (status considerados, data de referência)?

## 6. Perguntas de negócio

1. Qual a definição contratual do denominador das metas (inclui Pix? inclui transferências?).
2. Quanto o banco paga por ponto emitido? Qual a margem por modalidade (varejo próprio)?
3. Qual a meta de breakage e com que fórmula o diretor chegou a 40%?
4. Houve ação comercial ou operacional em 12/01/2026?
5. Por que os pushes caíram em agosto?
6. Há apetite para testar comunicação com grupo de controle?
