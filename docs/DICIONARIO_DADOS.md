# Dicionário de dados · fontes (CSV v1)

Construído a partir da exploração dos arquivos, porque o case não traz dicionário. Evidências em [EDA.md](EDA.md); classificação de cada campo em [CLASSIFICACAO_DADOS.md](CLASSIFICACAO_DADOS.md). As camadas gold estão documentadas em [catalog/gold.yml](../catalog/gold.yml), que também alimenta o agente.

Tipos: `id` = identificador numérico de 12 dígitos (texto, não é número de cartão; ver `pipeline/pan_check.py`); `ts` = `YYYY-MM-DD HH:MM:SS-03:00`; `ts_naive` = sem fuso.

## orders.csv · 1 linha por pedido · 19.785 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| order_id | id | 0 | Chave do pedido (única) |
| cart_id | id | 0 | Carrinho de origem (1:1 com carts) |
| user_id | id | **100%** | Sempre vazio. Usuário vem de `carts.user_id` |
| created_at | ts | 0 | Criação do pedido |
| status | texto | 0 | APROVADO, CANCELADO, FINALIZADO_COM_SUCESSO, ESTORNADO, INVALIDO, AGUARDANDO_CONFIRMACAO |
| status_updated_at | ts | 0 | Última mudança de status |

## order_items.csv · 1 linha por item · 19.803 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| order_item_id | id | 0 | Chave do item (única) |
| order_id | id | 0 | Pedido (18 pedidos têm 2 itens) |
| created_at | ts | 0 | Igual à criação do pedido |
| status | texto | 0 | Mesmo domínio do pedido; 4 itens divergem do status do pedido |
| product_type | texto | 0 | PASSAGEM, PRODUTO, TRANSFERENCIA, COMPRA_PONTOS |
| supplier_name | texto | 0 | Fornecedor (12 valores; "Pix Pontua+" = Pix) |
| supplier_responsible | texto | 0 | Responsável pelo pedido; difere em marketplace |
| category_macro | texto | 0 | Aereas, Varejo (inclui transferências para parceiros), Cashback (Pix + compra de pontos) |
| paid_points | inteiro | 520 | Pontos pagos; vazio só em COMPRA_PONTOS |
| paid_currency | decimal R$ | 0 | Copagamento em reais |
| product_value | decimal R$ | 0 | Valor do produto (hipótese: custo para o programa) |
| refunded_points | inteiro | 0 | Estorno parcial de pontos em itens aprovados |
| quantity | inteiro | 0 | Sempre 1 |

## carts.csv · 1 linha por carrinho · 19.785 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| cart_id | id | 0 | Chave do carrinho |
| user_id | id | 0 | Usuário (fonte oficial do usuário do pedido) |
| channel | texto | 0 | APP, WEB |

## points_ledger.csv · 1 linha por movimento de pontos · 146.739 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| movement_id | id | 0 | Chave do movimento |
| user_id | id | 0 | Usuário (bate com cards) |
| account_id | id | 0 | Conta/cartão (100% em cards) |
| operation_code | inteiro | 0 | FK para dim_operation; aparecem 1, 2, 14, 100, 103 |
| points | inteiro | 0 | Pontos com sinal (+ crédito, − débito) |
| movement_at | ts | 0 | Data do movimento |
| valid_until | data | 38.595 | Validade; só em créditos (código 1 = 2 anos; 100 = 31/03/2028) |

## dim_operation.csv · 1 linha por tipo de operação · 7 linhas

| Coluna | Tipo | Descrição |
|---|---|---|
| operation_code | inteiro | 1 CREDITO, 2 RESGATE, 3 EXPIRACAO, 13 ESTORNO_CREDITO, 14 ESTORNO_PEDIDO, 100 CREDITO_MIGRACAO, 103 EXPIRACAO_MIGRACAO |
| operation_name | texto | Nome |
| direction | texto | CREDIT ou DEBIT (coerente com o sinal de `points`) |

## cards.csv · 1 linha por conta/cartão · 16.168 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| account_id | id | 0 | Chave da conta (não é número de cartão) |
| user_id | id | 0 | Usuário (12.000 distintos) |
| card_class | texto | 0 | Essencial < Gold < Platinum < Platinum Elo < Infinite < Black |
| card_flag | texto | 0 | VISA, MASTERCARD, ELO |
| created_at | ts | 0 | Criação/emissão (8.708 movimentos são anteriores a ela) |
| is_most_recent | booleano | 0 | 1 cartão mais recente por usuário |

## redeemed_points.csv · 1 linha por movimento de pontos de um item numa conta · 29.838 linhas

| Coluna | Tipo | Descrição |
|---|---|---|
| order_item_id | id | Item (100% em order_items) |
| account_id | id | Conta debitada (2 linhas RESGATE = pagamento dividido entre contas) |
| movement_type | texto | RESGATE, RESERVA, CANCELADO_RESERVA (reserva e cancelamento se anulam) |
| points | inteiro | Pontos com sinal |

## crm_events.csv · 1 linha por evento · 348.250 linhas

| Coluna | Tipo | Nulos | Descrição |
|---|---|---|---|
| event_ts | ts_naive | 0 | Data/hora sem fuso (hipótese: local) |
| user_id | id | 20.252 | Recuperável 100% via device_id |
| device_id | texto | 0 | `DEV_` + hash; 1:1 com usuário |
| event_name | texto | 0 | Notification Sent/Viewed/Clicked/Failed, Push Impressions, Order Approved |
| campaign_type | texto | 17.494 | Email, Push, Mobile Push - Android/iOS, Facebook Audiences; vazio em Order Approved |
| campaign_id | texto | 17.494 | `CMP_...`; `CMP_LANCAMENTO_PIX_...` = lançamento do Pix |
| control_group | texto | **100%** | Sempre vazio: não há grupo de controle |
| event_properties | JSON | 0 | Chaves: campaign_name, open_count, link, reason, platform, audience, source |

## relatorio_mensal_cliente.csv · 1 linha por mês · 9 linhas

| Coluna | Tipo | Descrição |
|---|---|---|
| mes | YYYY-MM | Mês (jan a set/2026) |
| aereas_pct, varejo_pct, pix_pct | % | Participações reportadas pelo operador |
| pix_reais | R$ | Valor Pix reportado (≈ aprovados) |
| pix_pontos, pix_transacoes | inteiro | Pontos e transações Pix, **somando todos os status** |
| emails_enviados, push_enviados | inteiro | Envios reportados (push vazio até mar/26) |
